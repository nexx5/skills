import fs from "node:fs"
import os from "node:os"
import path from "node:path"
// 不能 import 包入口 "@opencode-ai/plugin"（dist/index.js 无扩展名导出，Node ESM 解析不到）。
// 必须用 exports 暴露的完整子路径 "/tool"。
import { tool } from "@opencode-ai/plugin/tool"

// ============ 配置（全局，跨项目共享） ============
const MOA_BOT_DIR = path.join(os.homedir(), ".config", "opencode", "moa-bot")
const STATE_FILE = path.join(MOA_BOT_DIR, "state.json")
const LOG_FILE = path.join(MOA_BOT_DIR, "moa-bot.log")
const LOCK_TTL_MS = 5000
const MOA_TAG_PREFIX = "[MOA-Bot"
// 高置信仲裁意图关键词
const TERMINATE_WORDS = ["终止", "结束", "停", "够了", "到此为止", "停止", "关闭"]
const REDIRECT_WORDS = ["方向", "改成", "换", "重点", "聚焦", "优先", "转向", "别再"]
const DEFAULT_MAX_ROUNDS = 20
// =================================================

// MOA-Bot plugin（全局版）：
//   - 基于现有会话的多 agent 协作：双方各自注册（自动配对，用户零配置），
//     内容经 moa_bot_submit 显式提交后注入对方会话（会话 ID 由 context.sessionID 自动获取）。
//   - 监听 event（step.ended/idle）判断对方完成；chat.message 解读人类仲裁自然语言。
//   - 生命周期：关闭即结束，不做跨启动恢复；新注册时自动清理失效的旧配对。
// SOP 在 MOA-Bot skill 的 SKILL.md（全局 ~/.config/opencode/skills/MOA-Bot/）。

export const MoaBot = async ({ client, directory }) => {
  const log = (msg) => {
    const line = `[${new Date().toISOString()}] ${msg}\n`
    try { fs.appendFileSync(LOG_FILE, line) } catch (e) {}
    try { client.app.log({ body: { service: "moabot", level: "info", message: msg } }).catch(() => {}) } catch (e) {}
  }

  let state = null // 当前活跃配对

  const ensureDir = () => {
    try { if (!fs.existsSync(MOA_BOT_DIR)) fs.mkdirSync(MOA_BOT_DIR, { recursive: true }) } catch (e) {}
  }
  const loadState = () => {
    ensureDir()
    try {
      const parsed = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"))
      state = parsed && Array.isArray(parsed.pairs) ? parsed : { pairs: [] }
    } catch (e) { state = { pairs: [] } }
  }
  const saveState = () => {
    ensureDir()
    try { fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2)) }
    catch (e) { log(`saveState 失败: ${e.message}`) }
  }

  // ---- 文件锁（跨项目实例互斥） ----
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

  // 会话是否仍活跃（用于清理失效配对）
  const isSessionAlive = async (sessionId) => {
    try {
      const res = await client.session.status({})
      const map = res?.data ?? res ?? {}
      return sessionId in map
    } catch (e) {
      try { await client.session.get({ path: { sessionID: sessionId } }); return true } catch (e2) { return false }
    }
  }

  // 找出某个会话所属的活跃配对（角色 + pair）
  const findPairBySession = (sessionId) => {
    if (!state?.pairs) return null
    for (const pair of state.pairs) {
      if (pair.status !== "active") continue
      for (const [role, info] of Object.entries(pair.roles || {})) {
        if (info.session_id === sessionId) return { pair, role }
      }
    }
    return null
  }

  // 向指定会话注入消息（带 MOA-Bot 标签，供识别防循环）
  const inject = async (sessionId, role, nav, text, kind = "draft") => {
    const msg = `${MOA_TAG_PREFIX}|from:${role || "system"}|nav:${nav}|kind:${kind}] ${text}`
    try {
      await client.session.prompt({
        path: { id: sessionId },
        body: { parts: [{ type: "text", text: msg }] }
      })
      log(`注入 ${sessionId.slice(0, 24)} [${kind}]: ${text.slice(0, 60)}`)
      return true
    } catch (e) {
      log(`注入失败 ${sessionId.slice(0, 24)}: ${e.message}`)
      return false
    }
  }

  const notifyBoth = async (pair, text) => {
    for (const [role, info] of Object.entries(pair.roles || {})) {
      await inject(info.session_id, role, pair.nav, text, "notice")
    }
  }

  // 从 state 移除失效配对（新注册时自动清理旧残留）
  const cleanupDeadPairs = async () => {
    const alive = []
    for (const pair of state.pairs || []) {
      let ok = true
      for (const info of Object.values(pair.roles || {})) {
        if (!(await isSessionAlive(info.session_id))) { ok = false; break }
      }
      if (ok) alive.push(pair)
      else log(`清理失效配对: ${pair.topic || "(untitled)"} (${Object.keys(pair.roles||{}).join("/")})`)
    }
    if (alive.length !== (state.pairs || []).length) { state.pairs = alive; saveState() }
  }

  // 配对是否就绪（≥2 角色）
  const pairReady = (pair) => pair && pair.roles && Object.keys(pair.roles).length >= 2

  // 注册/配对核心
  const register = async (args, context) => {
    const sid = context.sessionID
    if (!sid) return `未能拿到 session id。请检查 plugin 上下文。`
    const role = args.role?.trim()
    if (!role) return `请提供角色名 role。`
    if (/[\\/:*?"<>|]/.test(role)) return `角色名含非法字符（\\ / : * ? " < > |），请更换。`

    const lockFile = STATE_FILE + ".lock"
    let retry = 0
    while (!acquireLock(lockFile, `reg:${sid.slice(0, 12)}`) && retry < 3) {
      await new Promise(r => setTimeout(r, 300)); retry++
    }
    let result
    try {
      loadState()
      await cleanupDeadPairs()

      // 我自己已注册 -> 侧写更新
      const existing = findPairBySession(sid)
      if (existing) {
        existing.pair.roles[existing.role] = { ...existing.pair.roles[existing.role], session_id: sid }
        saveState()
        result = `你仍以角色「${existing.role}」注册在「${existing.pair.topic || "(untitled)"}」。`
        return result
      }

      // 找未满员的活跃/待定配对（首位未满员），否则建新配对
      let pair = (state.pairs || []).find(p => p.status !== "done" && !(role in (p.roles || {})) && Object.keys(p.roles || {}).length < 2)
      if (!pair) {
        pair = {
          topic: args.topic || "(untitled)",
          status: "pending",
          nav: 0,
          roles: {},
          max_rounds: args.max_rounds || DEFAULT_MAX_ROUNDS,
          created_at: new Date().toISOString(),
        }
        state.pairs.push(pair)
      }
      pair.roles[role] = { session_id: sid, joined_at: new Date().toISOString() }
      if (pairReady(pair)) pair.status = "active"
      saveState()
      log(`moa_bot_register: ${role} sid=${sid.slice(0, 24)} pair=${pair.topic || "(untitled)"} ready=${pair.status === "active"}`)
      result = `注册成功：你是「${role}」，配对议题「${pair.topic || "(untitled)"}」。`
      if (pair.status === "active") result += ` 已与另一角色配对（${Object.keys(pair.roles).filter(r => r !== role).join("、")}），MOA-Bot 已就绪。双方可各自工作，完成后用 moa_bot_submit 提交给对方。`
      else result += ` 等另一角色注册后自动配对。`
    } finally { releaseLock(lockFile) }
    return result
  }

  // 提交内容给对方（显式边界：仅提交内容进入对方会话）
  const submit = async (args, context) => {
    const sid = context.sessionID
    if (!sid) return `未能拿到 session id。`
    const content = args.content?.trim()
    if (!content) return `请提供要提交的内容 content。`

    const lockFile = STATE_FILE + ".lock"
    let retry = 0
    while (!acquireLock(lockFile, `sub:${sid.slice(0, 12)}`) && retry < 3) {
      await new Promise(r => setTimeout(r, 300)); retry++
    }
    try {
      loadState() // 锁内单次加载，避免 pair 引用与 state 分裂
      const found = findPairBySession(sid)
      if (!found) return `当前会话未注册为任何 MOA-Bot 角色。请先用 moa_bot_register 注册。`
      const { pair, role } = found
      const others = Object.entries(pair.roles || {}).filter(([r]) => r !== role)
      if (others.length === 0) return `对方角色尚未注册，暂时无法提交。`
      if (pair.nav >= (pair.max_rounds || DEFAULT_MAX_ROUNDS)) return `已达到轮次上限，请先终止本轮。`
      pair.nav += 1
      saveState()
      let deliverOk = true
      for (const [orole, oinfo] of others) {
        deliverOk = deliverOk && await inject(oinfo.session_id, role, pair.nav, content, "draft")
      }
      return deliverOk
        ? `已提交给 ${others.map(([r]) => r).join("、")}（回合 #${pair.nav}）。对方完成阅读后可用 moa_bot_submit 提交回应。`
        : `提交失败，请查日志 ${LOG_FILE}。`
    } finally { releaseLock(lockFile) }
  }

  // 人类仲裁：终止 / 方向调整 / 意见注入
  const arbitrate = async (sessionID, text) => {
    loadState()
    const found = findPairBySession(sessionID)
    if (!found) return null
    const { pair, role } = found
    const others = Object.entries(pair.roles || {}).filter(([r]) => r !== role)

    const termHit = TERMINATE_WORDS.some(w => text.includes(w))
    const redirHit = REDIRECT_WORDS.some(w => text.includes(w))

    if (termHit) {
      pair.status = "done"
      pair.ended_at = new Date().toISOString()
      pair.end_reason = `user_halt: ${text.slice(0, 80)}`
      saveState()
      const sum = others.map(([r]) => r).join("、")
      await notifyBoth({ ...pair, roles: pair.roles }, `用户已终止本轮 MOA（${text.slice(0, 60)}）。`)
      log(`用户终止: pair=${pair.topic} by ${role} text=${text.slice(0, 60)}`)
      return { action: "terminate", text }
    }

    if (redirHit) {
      const instruction = `${MOA_TAG_PREFIX}|from:H|action:redirect|round:${pair.nav}] 仲裁指令：${text}（请按新方向重新组织你的立场）`
      let ok = true
      const targets = others.length ? others : Object.entries(pair.roles || {})
      for (const [orole, oinfo] of targets) {
        ok = ok && await inject(oinfo.session_id, "H", pair.nav, text, "redirect")
      }
      log(`用户重定向: pair=${pair.topic} by ${role} text=${text.slice(0, 60)}`)
      return { action: "redirect", text }
    }

    // 普通意见 -> 作为 {H} 意见注入对手（下回合）
    const opinion = `${MOA_TAG_PREFIX}|from:H|action:opinion|round:${pair.nav}] 用户意见：${text}`
    for (const [orole, oinfo] of (others.length ? others : Object.entries(pair.roles || {}))) {
      await inject(oinfo.session_id, "H", pair.nav, text, "opinion")
    }
    log(`用户意见注入: pair=${pair.topic} by ${role} text=${text.slice(0, 60)}`)
    return { action: "opinion", text }
  }

  // 监听对方完成：step.ended / idle 时若有未读注入，提示来源角色（事件仅用于感知与日志，不自动转发——转发只由 moa_bot_submit 驱动）
  const onEvent = async (ev) => {
    try {
      const t = ev?.type
      const props = ev?.properties || {}
      if (t === "session.next.step.ended" || t === "session.idle") {
        const sid = props.sessionID
        if (!sid) return
        const found = findPairBySession(sid)
        if (!found) return
        log(`对方完成: ${found.role} (${t}) pair=${found.pair.topic}`)
      }
    } catch (e) { /* 事件钩子不能抛出 */ }
  }

  // 解读人类消息（chat.message 钩子）；注入的 MOA 消息带标签自动跳过
  const onChatMessage = async (input, output) => {
    try {
      const sessionID = input.sessionID
      if (!sessionID) return
      const parts = output?.parts || []
      const text = parts.map(p => (p.type === "text" ? (p.text || "") : (p.type === "reasoning" ? "" : (p.type === "input_text" ? (p.text || "") : "")))).join("\n").trim()
      if (!text) return
      if (text.includes(MOA_TAG_PREFIX)) return // 自己的注入，不当作人类仲裁
      await arbitrate(sessionID, text.slice(0, 500))
    } catch (e) { /* 不能抛出 */ }
  }

  // 启动：加载 state + 清理失效配对
  ensureDir()
  if (!fs.existsSync(STATE_FILE)) fs.writeFileSync(STATE_FILE, JSON.stringify({ pairs: [] }, null, 2))
  loadState()
  const instanceTag = `${directory} ${new Date().toISOString()}`
  log(`=== MOA-Bot plugin loaded (全局版) ${instanceTag} ===`)

  return {
    async dispose() {
      log(`MOA-Bot dispose (${instanceTag})`)
    },
    async event({ event: ev }) { await onEvent(ev) },
    "chat.message": onChatMessage,
    tool: {
      moa_bot_register: tool({
        description: "注册当前会话为 MOA-Bot 一方角色（对等，无主从）。参数：role（角色名，如 方案A/审核方/分析师，任意字符串）；topic（可选，配对议题，双方建议写一致）；max_rounds（可选，轮次上限，默认20）。双方各自在会话中注册后自动配对，互相识别由 plugin 完成，用户无需知道对方会话ID。请同时阅读 MOA-Bot skill 的 SKILL.md 沟通规范。",
        args: {
          role: tool.schema.string(),
          topic: tool.schema.string().optional(),
          max_rounds: tool.schema.number().optional(),
        },
        async execute(args, context) { return register(args, context) }
      }),
      moa_bot_submit: tool({
        description: "把深思熟虑后的定型内容提交给 MOA-Bot 配对中的对方会话（显式边界：只有调用本工具提交的内容才会进入对方会话，会话内的思考/草稿/工具过程不会外泄）。参数：content（要提交给对方的完整内容）。对方收到后会阅读并可用 moa_bot_submit 回应。",
        args: {
          content: tool.schema.string(),
        },
        async execute(args, context) { return submit(args, context) }
      }),
      moa_bot_halt: tool({
        description: "由用户手动终止当前会话所属的 MOA-Bot 配对。无参数。终止后本轮不再接力。",
        args: {},
        async execute(args, context) {
          const sid = context.sessionID
          loadState()
          const found = findPairBySession(sid)
          if (!found) return `当前会话未注册为任何 MOA-Bot 角色。`
          const { pair } = found
          pair.status = "done"
          pair.ended_at = new Date().toISOString()
          pair.end_reason = "user_halt_tool"
          saveState()
          await notifyBoth(pair, `用户手动终止了本轮 MOA。`)
          log(`moa_bot_halt: pair=${pair.topic}`)
          return `已终止「${pair.topic || "(untitled)"}」。`
        }
      }),
    },
  }
}