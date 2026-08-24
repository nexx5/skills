#!/usr/bin/env node
// MOA-Bot skill 部署脚本
// 功能：检查 moa-bot.js plugin 是否已部署到全局，未部署则自动部署（复制 plugin、
//       注册 opencode.json plugin 数组、初始化 state.json），并提示重启 opencode。
// 用法：
//   node deploy.js --check        仅检查部署状态，不改任何文件
//   node deploy.js [--force]      检查并自动部署；--force 强制覆盖已存在的 plugin 文件
// 退出码：0=已就绪/部署成功  2=未部署（--check 模式）  1=出错
import fs from "node:fs"
import os from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const SKILL_DIR = path.dirname(__dirname)                      // scripts/ 的上级 = skill 根目录
const PLUGIN_SRC = path.join(__dirname, "moa-bot.js")          // 本 skill 携带的 plugin 源文件

const OPENCODE_DIR = path.join(os.homedir(), ".config", "opencode")
const PLUGIN_DIR = path.join(OPENCODE_DIR, "plugin")
const PLUGIN_DEST = path.join(PLUGIN_DIR, "moa-bot.js")
const OPENCODE_JSON = path.join(OPENCODE_DIR, "opencode.json")
const MOA_BOT_DIR = path.join(OPENCODE_DIR, "moa-bot")
const STATE_FILE = path.join(MOA_BOT_DIR, "state.json")

const args = process.argv.slice(2)
const CHECK_ONLY = args.includes("--check")
const FORCE = args.includes("--force")

const green = (s) => `\x1b[32m${s}\x1b[0m`
const yellow = (s) => `\x1b[33m${s}\x1b[0m`
const red = (s) => `\x1b[31m${s}\x1b[0m`

function checkPluginFile() {
  return fs.existsSync(PLUGIN_DEST)
}

function checkJsonRegistered() {
  if (!fs.existsSync(OPENCODE_JSON)) return false
  let cfg
  try { cfg = JSON.parse(fs.readFileSync(OPENCODE_JSON, "utf8")) }
  catch (e) { return false }
  if (!Array.isArray(cfg.plugin)) return false
  const norm = (p) => path.normalize(p).replace(/\\/g, "/").toLowerCase()
  const target = norm(PLUGIN_DEST)
  return cfg.plugin.some((p) => typeof p === "string" && norm(p) === target)
}

function checkStateInit() {
  return fs.existsSync(STATE_FILE)
}

// 检查插件文件与本地副本是否一致（内容级别）
function pluginFileMatches() {
  if (!fs.existsSync(PLUGIN_DEST)) return false
  try {
    const a = fs.readFileSync(PLUGIN_SRC, "utf8")
    const b = fs.readFileSync(PLUGIN_DEST, "utf8")
    return a === b
  } catch (e) { return false }
}

function deploy() {
  // 1. 复制 plugin
  if (!fs.existsSync(PLUGIN_DIR)) fs.mkdirSync(PLUGIN_DIR, { recursive: true })
  if (fs.existsSync(PLUGIN_DEST) && !FORCE && !pluginFileMatches()) {
    console.log(yellow(`[跳过] ${PLUGIN_DEST} 已存在且与本 skill 副本不一致（可能被手动改过）。`))
    console.log(yellow(`       如需覆盖请运行：node ${path.join(SKILL_DIR, "scripts", "deploy.js")} --force`))
  } else {
    if (fs.existsSync(PLUGIN_DEST) && FORCE) {
      fs.copyFileSync(PLUGIN_DEST, PLUGIN_DEST + ".bak")
      console.log(yellow(`[备份] 旧 plugin 已备份到 ${PLUGIN_DEST}.bak`))
    }
    fs.copyFileSync(PLUGIN_SRC, PLUGIN_DEST)
    console.log(green(`[部署] plugin -> ${PLUGIN_DEST}`))
  }

  // 2. 注册 opencode.json plugin 数组
  if (checkJsonRegistered()) {
    console.log(green(`[OK] opencode.json 已注册 moa-bot.js`))
  } else if (fs.existsSync(OPENCODE_JSON)) {
    const raw = fs.readFileSync(OPENCODE_JSON, "utf8")
    let cfg
    try { cfg = JSON.parse(raw) }
    catch (e) {
      console.log(red(`[失败] ${OPENCODE_JSON} 不是合法 JSON，跳过自动注册。请手动在 "plugin" 数组加入：`))
      console.log(red(`       "${PLUGIN_DEST.replace(/\\/g, "\\\\")}"`))
      process.exit(1)
    }
    if (!Array.isArray(cfg.plugin)) cfg.plugin = []
    fs.copyFileSync(OPENCODE_JSON, OPENCODE_JSON + ".bak")
    cfg.plugin.push(PLUGIN_DEST)
    fs.writeFileSync(OPENCODE_JSON, JSON.stringify(cfg, null, 2) + "\n", "utf8")
    console.log(green(`[注册] opencode.json plugin 数组已追加（旧配置备份为 opencode.json.bak）`))
  } else {
    const cfg = { plugin: [PLUGIN_DEST.replace(/\\/g, "\\\\")] }
    fs.writeFileSync(OPENCODE_JSON, JSON.stringify(cfg, null, 2) + "\n", "utf8")
    console.log(green(`[新建] 创建 ${OPENCODE_JSON} 并注册 plugin`))
  }

  // 3. 初始化 state.json（独立于旧 MOA 的 tasks.json，二者互不干扰）
  if (checkStateInit()) {
    console.log(green(`[OK] ${STATE_FILE} 已存在`))
  } else {
    if (!fs.existsSync(MOA_BOT_DIR)) fs.mkdirSync(MOA_BOT_DIR, { recursive: true })
    fs.writeFileSync(STATE_FILE, JSON.stringify({ pairs: [] }, null, 2) + "\n", "utf8")
    console.log(green(`[初始化] ${STATE_FILE}`))
  }
}

console.log(`MOA-Bot skill 目录：${SKILL_DIR}`)
console.log(`目标 plugin：${PLUGIN_DEST}`)

const fileOk = checkPluginFile()
const jsonOk = checkJsonRegistered()
const stateOk = checkStateInit()

if (CHECK_ONLY) {
  console.log("")
  console.log(fileOk ? green("  [OK] plugin 文件已部署") : red("  [缺失] plugin 文件未部署"))
  console.log(jsonOk ? green("  [OK] opencode.json 已注册") : red("  [缺失] opencode.json 未注册 plugin"))
  console.log(stateOk ? green("  [OK] state.json 已初始化") : red("  [缺失] state.json 未初始化"))
  console.log("")
  if (fileOk && jsonOk && stateOk) {
    console.log(green("MOA-Bot 已就绪。"))
    process.exit(0)
  }
  console.log(yellow("未完全部署。运行以下命令自动部署，完成后重启 opencode："))
  console.log(yellow(`  node "${path.join(SKILL_DIR, "scripts", "deploy.js")}"`))
  process.exit(2)
}

deploy()

const finalFile = checkPluginFile()
const finalJson = checkJsonRegistered()
const finalState = checkStateInit()

console.log("")
if (finalFile && finalJson && finalState) {
  console.log(green("✓ 部署完成，全部就绪。"))
  console.log(yellow(">>> 请重启 opencode 使 plugin 生效（plugin 仅加载时扫描一次）。重启后新会话应可见 moa_bot_register / moa_bot_submit / moa_bot_halt 工具。"))
  process.exit(0)
}
console.log(red("部署未完全完成，请检查上面的输出。"))
process.exit(1)