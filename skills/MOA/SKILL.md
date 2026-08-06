---
name: MOA
description: "MOA（多模型协作）跨会话审稿沟通规范。通过文件传话实现双方角色的迭代碰撞：plugin 负责传话，会话按本规范读写文件。使用场景：(1) 启动新 MOA，调 moa_register 注册角色+输出模式+监听目录，双方注册同一目录后自动配对启动；(2) 收到'那边说：见 {文件名}，你继续'消息时，读对方文件并按角色输出自己的文件；(3) 需要让两个不同模型的会话做迭代碰撞（方案/审核、分析/评论等任意双方角色）。覆盖前置部署检查、角色职责、文件命名规则、输出三段格式（共识项/已采纳修订/分歧）、终止标记、任务文件清理与故障排查。传话执行由 moa-trigger plugin 负责（随本 skill 的 scripts/ 目录分发），本规范不含执行逻辑。"
---

# MOA 沟通规范（SOP）

> 你参与 MOA（多模型协作）。plugin 只负责传话，你按本规范处理。
> plugin 发的消息固定格式："对方说：见 {文件名}，你继续"

## 部署与前置准备（首次使用必须先做）

MOA 依赖 `moa-trigger` plugin（传话引擎），plugin 本体在本 skill 的 `scripts/moa-trigger.js`，需部署为**全局 plugin**（opencode 的 `~/.config/opencode/plugin/`）并注册进 `opencode.json` 的 `plugin` 数组。

**运行前检查**：在项目目录执行

```powershell
node "<skill目录>/scripts/deploy.js" --check
```

**未部署时自动部署**：

```powershell
node "<skill目录>/scripts/deploy.js"
```

脚本会：① 复制 `moa-trigger.js` 到全局 plugin 目录；② 若 `opencode.json` 的 `plugin` 数组未包含则追加（自动备份 `.bak`）；③ 初始化全局任务文件 `~/.config/opencode/moa/tasks.json`。

**部署后必须重启 opencode**：plugin 只在启动时加载扫描一次，重启后新会话才可见 `moa_register` 工具。

> 若无法执行脚本（无 node 或路径受限），手动部署：复制 `scripts/moa-trigger.js` 到 `~/.config/opencode/plugin/`，在 `opencode.json` 的 `"plugin"` 数组追加该文件的绝对路径，重启 opencode。

**就绪判定**：重启后任意会话能看到 `moa_register` 工具即部署成功（见「故障排查」首行）。

## 收到消息后

收到"对方说：见 {文件名}，你继续"：
1. 读该文件（在注册的 watch_dir 下）
2. 按你的角色处理
3. 输出你的文件（按注册的 output_pattern 命名，{n} 递增）
4. 达成一致或分歧无法合拢时，写终止标记

## 启动一个新 MOA

> plugin 已全局注册（所有项目、所有会话可见 `moa_register`）。按以下步骤配对：

1. **确认议题**：本次 MOA 要审什么、产出什么
2. **定角色 + 模型**：两个角色名自定义（如 方案方/审核方、分析员/评论员、作者/编辑）；**双方尽量用不同模型才有碰撞意义**（如 glm-5.2 ↔ deepseek-v4-flash）
3. **定 watch_dir**：监听目录。新议题建议建独立目录（如 `<议题名>-moa/`），避免文件互相干扰
4. **本会话注册**：调用 `moa_register`，参数：
   - `role`：你的角色名（任意字符串，如 `方案方` / `分析员` / `A角`）
   - `output_pattern`（可选）：输出文件名模式，默认 `{角色}-第{n}版.md`（`{n}` 递增）
   - `watch_dir`（可选）：监听目录。不指定则用按日期的临时目录（`~/.config/opencode/moa/tmp/<日期>`），同一天双方自动配对，MOA 结束后自动清理
5. **告知对方**：去另一个会话（**可在不同项目**）注册**同一个 watch_dir**、另一个 role
6. **双方就绪**：plugin 检测双方注册后自动启动，双方都收到"MOA就绪，你可以开始输出"。谁先输出由用户指令决定；若 60s 无动静，先注册方默认先输出（兜底）

## 配对边界

- **必须注册同一个 watch_dir** 才配对；可在不同项目、不同模型
- MOA 期间保持**至少一方项目打开**（plugin 实例随项目存在）
- 一个 watch_dir 同时只跑一个 MOA 任务；不同议题用不同 watch_dir

## 多 MOA 并行（同一时间跑多组）

- **隔离键 = watch_dir**：plugin 以 `watch_dir` 作为任务唯一键（`tasks.json` 按目录区分任务），一个目录只承载一组 MOA。多组并行 = 各组**指定不同的 watch_dir**
- **默认临时目录不适合并行**：不指定 watch_dir 时落到 `~/.config/opencode/moa/tmp/<日期>`，同一日期所有未指定目录的注册会合并进**同一个任务**，传话配对错乱（plugin 只认第一个非己角色作接收方）。同一天并行多组，也必须各自指定独立 watch_dir——目录不同即可，日期可以相同
- **各组互不干扰**：不同 watch_dir 各自配对、各自传话、各自终止，文件与锁互不冲突；清理时按 watch_dir 区分条目，只删对应组的 `done` 任务
- **判定标准**：注册返回里包含"注意：默认目录已有其他活跃任务，建议指定独立 watch_dir"时，说明你在和别的组共用临时目录，必须改用独立 watch_dir

## 角色

角色名注册时自定义（任意字符串，如 A角/B角、方案方/审核方、分析员/评论员）。**双方对等**：都输出、都响应，无固定主从。谁先输出由用户指令决定，不由注册顺序决定。若未收到用户指令且 60s 内无任何方输出，先注册方默认先输出（兜底防死等，用户指令优先）。

> 示例：A角/B角（通用）、方案方/审核方（方案评审）、分析员/评论员（分析评论）。角色名只影响通知消息里的称呼和文件名，传话/终止机制角色无关。

## 输出格式（每次文件三段）

```
### 共识项
（双方已达成一致的，简列）

### 已采纳修订
（本轮采纳的对方意见，简列）

### 分歧
（仍未达成一致的，说明各方立场）
```

## 终止

- 共识项全覆盖、无分歧 -> 文件末尾写 `<!-- MOA: consensus -->`
- 分歧无法合拢 -> 文件末尾写 `<!-- MOA: deadlock -->`
- **终止标记由后注册方（B角）写**（收尾动作）

写终止标记后，plugin 停止 MOA，通知双方。

> **重要**：MOA 文件中**不得在正文引用完整终止标记字符串**（哪怕举例）。plugin 检测文件末尾 200 字符，正文引用会被误判为终止。如需提及，用"共识标记"/"死锁标记"代替。

## 原则

- **不重复对方已说的**，只列增量
- 共识/已采纳简列，分歧详述
- 你的文件是你的产出，对方会读
- **简洁**：对方读得懂就行，不要长篇
- 文件名严格按 output_pattern，{n} 递增，让 plugin 能匹配
- **MOA 过程中只讨论，不执行修改**：不改动代码/配置/文件（只读分析可以，如读代码理解现状）。实际改动在 MOA 结束、共识达成后执行

## 维护

### 清理已完成任务

**触发时机**：MOA 正常终止后（收到"MOA结束"通知、`status=done`）**立即清理，不攒批**。

**责任方**：由**输出方**（先注册的角色）执行清理（输出方写终止标记，最清楚结束状态）。若输出方会话已关闭，响应方兜底。双方勿同时清理--执行前先 Read `tasks.json`，若 `tasks.json.bak` 存在且新鲜（<30s），说明他方正在清理，等 30s 再试。

**流程**：

1. **备份**：复制 `~/.config/opencode/moa/tasks.json` -> `tasks.json.bak`（覆盖旧备份）
2. **Read** `tasks.json`，确认哪些任务 `status=done` 且不再需要
3. **只删除 `done` 条目**；`pending`/`active`（进行中）任务**绝不能删**
4. **写回**：用 Write 工具或 node 写回（保持 `[]` 数组结构）
5. **写回后立即校验** JSON 合法：
   ```powershell
   node -e "JSON.parse(require('fs').readFileSync(process.env.USERPROFILE + '/.config/opencode/moa/tasks.json','utf8')); console.log('JSON OK')"
   ```
   无 node 时用 Read 工具读回，确认是合法 JSON 数组
6. **校验失败立即回滚**：用 `tasks.json.bak` 覆盖 `tasks.json`，重新校验
7. 清理后**重启生效无需等待**--plugin 每次轮询前重新 loadTasks，删掉条目即不再处理

**硬约束（违反即事故）**：
- 只删 `done`，`pending`/`active` 绝不删--误删进行中任务会导致该 MOA 无法传话
- 写回前必须备份；写回后必须校验，校验失败立即回滚
- JSON 写坏会导致 plugin `loadTasks` 解析失败回退 `tasks=[]`，**全部任务丢失**
- 历史方案文件保留在各自 watch_dir，不受清理影响

### 故障排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 会话看不到 `moa_register` | plugin 未部署 / 旧会话未加载 | 运行 `deploy.js --check` 确认部署状态；已部署则重启 opencode（plugin 启动时才扫描一次）；确认全局 opencode.json plugin 数组已注册 moa-trigger.js |
| 双方都注册了但不启动 | watch_dir 不一致 / 任务文件异常 | 核对两边 watch_dir；查看 `~/.config/opencode/moa/moa-trigger.log` |
| 传话不达 | 对方会话已关闭 / notify 失败 | 确认对方项目开着；查日志 `notify 失败` |
| 重复传话 | 锁未生效（旧版 plugin 还在跑） | 确认项目级旧 plugin 已移除；重启 |
| 任务停摆 | 所有项目都关闭 / 锁残留（<5s 内） | 打开任一项目；等 5s 或手动删 `*.moa.lock` |
| 误判终止 | 文件正文引用了完整终止标记字符串 | 正文用"共识标记"/"死锁标记"代替；按本规范约定 |
