import fs from "node:fs"
import os from "node:os"
import path from "node:path"
// 注意：不能 import 包入口 "@opencode-ai/plugin"（其 dist/index.js 无扩展名导出，
// Node ESM 解析不到 "./tool" 会挂掉）。必须用 exports 暴露的完整子路径 "/tool"。
import { tool } from "@opencode-ai/plugin/tool"

// ============ 配置（全局，跨项目共享） ============
const MOA_DIR = path.join(os.homedir(), ".config", "opencode", "moa")
const TASKS_FILE = path.join(MOA_DIR, "tasks.json")
const LOG_FILE = path.join(MOA_DIR, "moa-trigger.log")
const TERMINATION_MARKS = ["<!-- MOA: consensus -->", "<!-- MOA: deadlock -->"]
const LOCK_TTL_MS = 5000   // 文件锁有效期：超过视为失效可抢占
// =================================================
// MOA trigger plugin（全局版）：
//   - 全局注册：所有项目、所有会话可见 moa_register
//   - 全局单任务文件：~/.config/opencode/moa/tasks.json（默认空 []，跨项目共享）
//   - 跨项目多实例：每个打开的项目各加载一份实例，都轮询同一任务文件；
//     处理前抢文件锁（<文件>.moa.lock），锁龄 <5s 跳过 → 杜绝重复传话
//   - 文件更新 -> 向对方发"那边说：见 {文件名}，你继续"
//   - 终止标记（文件末尾） -> 停止 + 通知双方 + 写回 done
// SOP 在 MOA skill 的 SKILL.md（全局 ~/.config/opencode/skills/MOA/ 或项目 .opencode/skills/MOA/，
// 会话读，plugin 不含流程逻辑）

export const MoaTrigger = async ({ client, directory }) => {
  const log = (msg) => {
    const line = `[${new Date().toISOString()}] ${msg}\n`
    try { fs.appendFileSync(LOG_FILE, line) } catch (e) {}
    console.log(`[moa] ${msg}`)
    client.app.log({ body: { service: "moa", level: "info", message: msg } }).catch(() => {})
  }

  let tasks = []
  const watchers = {}

  const ensureDir = () => {
    try { if (!fs.existsSync(MOA_DIR)) fs.mkdirSync(MOA_DIR, { recursive: true }) } catch (e) {}
  }
  const loadTasks = () => {
    ensureDir()
    try { tasks = JSON.parse(fs.readFileSync(TASKS_FILE, "utf8")) || [] }
    catch (e) { tasks = [] }
  }
  const saveTasks = () => {
    ensureDir()
    try { fs.writeFileSync(TASKS_FILE, JSON.stringify(tasks, null, 2)) }
    catch (e) { log(`saveTasks 失败: ${e.message}`) }
  }

  // ---- 文件锁（跨实例互斥） ----
  // 锁存在且新鲜（<LOCK_TTL_MS）→ 有人正在处理，跳过；过期 → 视为失效可抢占
  const acquireLock = (lockFile, owner) => {
    try {
      const fresh = fs.existsSync(lockFile) && (Date.now() - fs.statSync(lockFile).mtimeMs) < LOCK_TTL_MS
      if (fresh) return false
      fs.writeFileSync(lockFile, `${owner} @ ${new Date().toISOString()}`)
      return true
    } catch (e) { return false }
  }
  const releaseLock = (lockFile) => {
    try { if (fs.existsSync(lockFile)) fs.unlinkSync(lockFile) } catch (e) {}
  }
  // 清理 watch_dir 下的 .moa.lock 文件
  // mode: "expired" 只删过期的（mtime > LOCK_TTL_MS）；"all" 删全部（任务终止时收尾）
  const cleanLocks = (watch_dir, mode) => {
    try {
      for (const f of fs.readdirSync(watch_dir)) {
        if (!f.endsWith('.moa.lock')) continue
        const fp = path.join(watch_dir, f)
        try {
          if (mode === 'all' || (Date.now() - fs.statSync(fp).mtimeMs) > LOCK_TTL_MS) fs.unlinkSync(fp)
        } catch (e) {}
      }
    } catch (e) {}
  }

  const notify = async (sessionId, message) => {
    try {
      await client.session.prompt({
        path: { id: sessionId },
        body: { parts: [{ type: "text", text: message }] }
      })
      log(`通知 ${sessionId.slice(0, 24)}: ${message.slice(0, 80)}`)
    } catch (e) { log(`notify 失败: ${e.message}`) }
  }

  // 文件名模式 -> 正则（{n} -> \d+）
  const patternToRegex = (pattern) => {
    const escaped = pattern.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace("\\{n\\}", "\\d+")
    return new RegExp("^" + escaped + "$")
  }

  // 终止检测：只看文件末尾200字符，避免文件中间引用的标记误判
  const checkTermination = (filePath) => {
    try {
      const content = fs.readFileSync(filePath, "utf8")
      const tail = content.slice(-200)
      for (const mark of TERMINATION_MARKS) {
        if (tail.includes(mark)) return mark
      }
    } catch (e) {}
    return null
  }

  let _handling = false  // running 锁：防本实例内并发重复
  const handleFileEvent = async (task, filename, instanceTag) => {
    if (filename.endsWith('.moa.lock')) return
    cleanLocks(task.watch_dir, "expired")
    if (_handling) return
    _handling = true
    try {
      const filePath = path.join(task.watch_dir, filename)
      // 跨实例互斥：抢不到锁说明其他项目实例正在处理，跳过
      const lockFile = filePath + ".moa.lock"
      if (!acquireLock(lockFile, instanceTag)) return
      try {
        let toSession = null, fromRole = null
        for (const [role, info] of Object.entries(task.roles)) {
          if (patternToRegex(info.output_pattern).test(filename)) {
            fromRole = role
            const other = Object.entries(task.roles).find(([r]) => r !== role)
            toSession = other ? other[1].session_id : null
            break
          }
        }
        if (!toSession) return  // 非双方输出文件，忽略
        // 终止检测
        const term = checkTermination(filePath)
        if (term) {
          log(`终止标记 ${term}（${fromRole}），任务结束`)
          const curTask = tasks.find(t => t.watch_dir === task.watch_dir)
          if (curTask) { curTask.status = "done"; saveTasks() }
          for (const info of Object.values(task.roles)) {
            await notify(info.session_id, `MOA结束：${fromRole}发出 ${term}`)
          }
          if (watchers[task.watch_dir]) { clearInterval(watchers[task.watch_dir]); delete watchers[task.watch_dir] }
          cleanLocks(task.watch_dir, "all")
          if (curTask?.tmp_dir) {
            try {
              for (const f of fs.readdirSync(task.watch_dir)) {
                if (f.endsWith('.md') || f.endsWith('.moa.lock')) fs.unlinkSync(path.join(task.watch_dir, f))
              }
              log(`临时目录已清理: ${task.watch_dir}`)
            } catch (e) {}
          }
          return
        }
        // 传话（最简单 prompt）
        await notify(toSession, `那边说：见 ${filename}，你继续`)
      } finally { releaseLock(lockFile) }
    } finally { _handling = false }
  }

  const startWatch = (task, instanceTag) => {
    if (watchers[task.watch_dir]) return
    const fileMtimes = {}
    let initialized = false
    const poll = () => {
      // 任务已终止则停止轮询（双保险：clearInterval 不生效时靠这个停）
      const curTask = tasks.find(t => t.watch_dir === task.watch_dir)
      if (curTask && curTask.status === "done") {
        if (watchers[task.watch_dir]) { clearInterval(watchers[task.watch_dir]); delete watchers[task.watch_dir] }
        log(`任务已终止，停止轮询: ${task.watch_dir}`)
        return
      }
      try {
        for (const filename of fs.readdirSync(task.watch_dir)) {
          const filePath = path.join(task.watch_dir, filename)
          try {
            const mtime = fs.statSync(filePath).mtimeMs
            // initialized 后：新文件（undefined）或 mtime 变化 -> 触发
            if (initialized && (fileMtimes[filePath] === undefined || fileMtimes[filePath] !== mtime)) {
              handleFileEvent(task, filename, instanceTag)
            }
            fileMtimes[filePath] = mtime
          } catch (e) {}
        }
      } catch (e) {}
      initialized = true
    }
    poll()  // 初始化基线 mtime（不触发）
    watchers[task.watch_dir] = setInterval(poll, 2000)
    log(`轮询监听: ${task.watch_dir}`)
  }

  const checkReady = (instanceTag) => {
    for (const task of tasks) {
      const roleList = Object.keys(task.roles)
      if (task.status === "pending" && roleList.length >= 2 && roleList.every(r => task.roles[r].session_id)) {
        task.status = "active"
        saveTasks()
        startWatch(task, instanceTag)
        for (let i = 0; i < roleList.length; i++) {
          const role = roleList[i]
          const isLast = (i === roleList.length - 1)
          const termHint = isLast ? '终止标记由你写（后注册方）。' : '终止标记由对方写。'
          notify(task.roles[role].session_id, `MOA就绪，对方已注册。你可以开始输出（${role}）。${termHint}`)
        }
      }
    }
  }

  // 启动：加载已有任务 + 监听任务文件
  ensureDir()
  if (!fs.existsSync(TASKS_FILE)) fs.writeFileSync(TASKS_FILE, "[]")
  const instanceTag = `${directory} ${new Date().toISOString()}`
  loadTasks()
  for (const task of tasks) {
    if (task.status === "active") {
      cleanLocks(task.watch_dir, "expired")
      startWatch(task, instanceTag)
    } else if (task.status === "done" && task.tmp_dir) {
      try {
        for (const f of fs.readdirSync(task.watch_dir)) {
          if (f.endsWith('.md') || f.endsWith('.moa.lock')) fs.unlinkSync(path.join(task.watch_dir, f))
        }
        log(`启动兜底清理临时目录: ${task.watch_dir}`)
      } catch (e) {}
    }
  }
  checkReady(instanceTag)
  try {
    let taskDebounce
    fs.watch(TASKS_FILE, () => {
      clearTimeout(taskDebounce)
      taskDebounce = setTimeout(() => {
        loadTasks()
        checkReady(instanceTag)
        for (const task of tasks) {
          if (task.status === "active") startWatch(task, instanceTag)
        }
      }, 1000)
    })
  } catch (e) { log(`监听任务文件失败: ${e.message}`) }

  log("=== MOA trigger plugin loaded (全局版) ===")

  return {
    tool: {
      moa_register: tool({
        description: "注册当前会话为MOA一方。参数：role（角色名，任意）；output_pattern（可选，默认 {角色}-第{n}版.md）；watch_dir（可选，默认按日期的临时目录，结束自动清理）。双方注册同一watch_dir后自动配对启动。请同时阅读 MOA skill 的 SKILL.md 沟通规范（全局或项目 skill 目录内）。",
        args: {
          role: tool.schema.string(),
          output_pattern: tool.schema.string().optional(),
          watch_dir: tool.schema.string().optional(),
        },
        async execute(args, context) {
          const sid = context.sessionID
          if (!sid) {
            return `未能拿到 session id。请检查 plugin 上下文。`
          }
          // 角色名合法性校验（Windows 文件名非法字符）
          if (/[\\/:*?"<>|]/.test(args.role)) {
            return `角色名含非法字符（\\ / : * ? " < > |），请更换。`
          }
          // 默认值：output_pattern 未指定则 {角色}-第{n}版.md；watch_dir 未指定则按日期的临时目录
          if (!args.output_pattern) args.output_pattern = `${args.role}-第{n}版.md`
          const isTmp = !args.watch_dir
          if (isTmp) {
            const d = new Date()
            const dateStr = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
            args.watch_dir = path.join(MOA_DIR, "tmp", dateStr)
          }
          // 写任务前加锁（低频操作，防跨实例并发覆盖）
          const taskLock = TASKS_FILE + ".lock"
          if (!acquireLock(taskLock, `register:${sid.slice(0, 12)}`)) {
            // 锁被占：等 300ms 重试一次
            await new Promise(r => setTimeout(r, 300))
          }
          let task, dirWarn = false
          try {
            loadTasks()
            dirWarn = isTmp && tasks.some(t => t.watch_dir === args.watch_dir && t.status === "active" && !(args.role in (t.roles || {})))
            task = tasks.find(t => t.watch_dir === args.watch_dir)
            if (!task) {
              task = { watch_dir: args.watch_dir, status: "pending", roles: {}, tmp_dir: isTmp }
              tasks.push(task)
            }
            task.roles[args.role] = { session_id: sid, output_pattern: args.output_pattern }
            saveTasks()
          } finally { releaseLock(taskLock) }
          if (isTmp) { try { fs.mkdirSync(args.watch_dir, { recursive: true }) } catch (e) {} }
          checkReady(instanceTag)
          const ready = task?.roles && Object.keys(task.roles).length >= 2 && Object.values(task.roles).every(r => r.session_id)
          log(`moa_register: ${args.role} sid=${sid.slice(0, 24)} ${ready ? "双方就绪" : "等对方"}`)
          const regCount = task.roles ? Object.keys(task.roles).length : 0
          const isLast = ready && regCount >= 2
          return `注册成功：你是${args.role}，输出模式 ${args.output_pattern}，目录 ${args.watch_dir}${isTmp ? "（临时，结束自动清理）" : ""}。${dirWarn ? "注意：默认目录已有其他活跃任务，建议指定独立 watch_dir。" : ""}${ready ? `双方就绪，MOA启动。${isLast ? "你是后注册方，终止标记由你写。" : ""}` : "等对方注册。"} 请阅读 MOA skill 的 SKILL.md 遵循沟通规范。`
        }
      })
    }
  }
}
