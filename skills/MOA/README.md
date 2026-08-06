# MOA 使用说明（README）

> MOA = 跨会话多模型协作。plugin 负责传话，双方会话按 SKILL.md 处理，用户可中途介入。
> 本文件说明部署前置、架构、快速开始、维护与故障排查。

## 部署与前置准备

MOA 依赖 `moa-trigger` plugin（传话引擎），随本 skill 的 `scripts/moa-trigger.js` 分发。首次使用需部署为全局 plugin：

```powershell
node "<skill目录>/scripts/deploy.js" --check   # 检查是否已部署
node "<skill目录>/scripts/deploy.js"           # 未部署则自动部署（复制 plugin + 注册 opencode.json + 初始化 tasks.json）
```

部署后**必须重启 opencode** 才生效。就绪判定：重启后任意会话可见 `moa_register` 工具。

## 架构

```
┌─ 全局层（能力）────────────────────────────────┐
│  ~/.config/opencode/plugin/moa-trigger.js
│    全局注册（opencode.json plugin 数组）-> 所有项目、所有会话可见 moa_register
│  ~/.config/opencode/moa/tasks.json     ← 全局单任务文件（默认空 []，跨项目共享）
│  ~/.config/opencode/moa/moa-trigger.log ← 全局日志
└───────────────────────────────────────────────┘
        ▲ 所有项目实例共享
┌─ 项目层（实例化）──────────────────────────────┐
│  每个打开的项目加载一份 plugin 实例             │
│  实例间通过文件锁（<文件>.moa.lock）互斥        │
│  同一任务只被一个实例处理 -> 跨项目不重复传话    │
└───────────────────────────────────────────────┘
```

**核心设计**：
- 任务文件全局唯一 -> 角色A在项目 A、角色B在项目 B 可配对（注册同一 watch_dir，角色名任意）
- 每个项目实例都轮询任务 -> 抢文件锁后只有一个实例执行处理 -> 不重复
- 锁龄超 5 秒视为失效可抢占 -> 进程崩溃残留锁不影响后续

## 快速开始

### 场景一：同项目配对（最常见）
> 角色名任意（方案方/审核方、分析员/评论员等），下方以方案方/审核方为例。
1. 会话 A（如 glm-5.2）调 `moa_register`：
   - `role=方案方`、`output_pattern=方案-第{n}版.md`、`watch_dir=<你的监听目录>`
2. 会话 B（如 deepseek-v4-flash）调 `moa_register`：
   - `role=审核方`、`output_pattern=审核意见-第{n}版.md`、`watch_dir=<同一个目录>`
3. 双方就绪，plugin 自动启动；双方都收到"你可以开始输出"，谁先输出由用户指令决定 -> 往返传话 -> 终止标记结束（由后注册方写）

### 场景二：跨项目配对
1. 在项目 A 的会话注册角色 A（watch_dir 指向共享目录，如 `<SHARED_DIR>`）
2. 在项目 B 的会话注册角色 B（**同一个 watch_dir**）
3. 双方就绪后同样自动运行；A、B 任一项目保持打开即可

### 快速开始要点
- 双方必须注册**同一个 watch_dir** 才配对
- 新议题建议建独立目录（`<议题名>-moa/`），避免与旧任务文件互相干扰
- 双方用不同模型，碰撞才有意义

## 文件锁机制

- 锁文件：`<被处理文件>.moa.lock`（处理完自动删除）
- 写任务时：`tasks.json.lock`（低频注册，300ms 重试兜底）
- 锁龄 <5s：其他实例跳过；>5s：视为失效可抢占
- 正常情况下锁会随处理结束释放；异常崩溃会残留，但 5 秒后自动视为失效，无需手工清理（除非想立即恢复，可手动删除）

## 维护建议（重要）

1. **清理任务文件**：MOA 正常终止后立即清理 `~/.config/opencode/moa/tasks.json` 中 `status=done` 的条目（不攒批）。
   - 执行流程见 `SKILL.md`「维护·清理已完成任务」（含备份/校验/回滚）
   - 要点：只删 `done`，`pending/active` 绝不删；写前备份 `tasks.json.bak`；写后校验，失败回滚
2. **日志**：`~/.config/opencode/moa/moa-trigger.log` 记录注册、轮询、传话、终止全过程，排查用
3. **历史归档**：已结束 MOA 的方案文件保留在各自 watch_dir 下即可，任务文件条目可删

## 故障排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 会话看不到 `moa_register` | plugin 未部署 / 重启前旧会话 | 运行 `deploy.js --check`；已部署则重启 opencode；确认全局 opencode.json plugin 数组已注册 |
| 双方都注册了但不启动 | watch_dir 不一致 / 任务文件异常 | 核对两边 watch_dir；查看日志 |
| 传话不达 | 对方会话已关闭 / notify 失败 | 确认对方项目开着；查看日志 `notify 失败` |
| 重复传话 | 锁未生效（旧版 plugin 还在跑） | 确认项目级旧 plugin 已移除；重启 |
| 任务停摆 | 所有项目都关闭 / 锁残留（<5s 内） | 打开任一项目；等 5s 或手动删锁 |
| 误判终止 | 文件正文引用了完整终止标记字符串 | 正文用"共识标记"等代替；按 SKILL.md 约定 |

## 变更记录

- 2026-08-06 全局化升级：plugin 从项目级硬编码 -> 全局注册 + 全局单任务文件 + 文件锁跨项目多实例；SKILL.md 增加启动引导/配对边界/维护；本 README 新建
- 2026-08-06 bug 修复 + 通用化：修复注册作用域/lock循环/正则锚定 3 bug；新增 cleanLocks 自动清理；角色名从硬编码方案方/审核方改为任意自定义（task.roles 动态结构）；SKILL.md 维护段补责任方/触发时机/备份恢复
- 2026-08-06 正式版收纳：js 归入 scripts/ 分发；新增 deploy.js 部署检查/自动部署/重启提示；改写死路径为 skill 相对引用
