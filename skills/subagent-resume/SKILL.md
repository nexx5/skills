---
name: subagent-resume
description: 接续中断的 sub agent，避免从头重派浪费。
---
# 定位与功能
父 agent 传入派发时的任务名称，skill 查询 opencode 数据库匹配 sub agent session，返回 task_id（task_id = subagent session id，持久化在 opencode.db，重启不丢）+ 中断状态，供调用者用 Task 工具的 task_id 参数恢复接续。支持多级 sub agent 逐级追索接续。适用场景：(1) sub agent 返回空结果/报错/未完成，(2) 预期产出缺失怀疑 sub agent 中断，(3) 重启 opencode 后恢复未完成的 sub agent 任务，(4) sub agent 自身因下级 sub-sub agent 中断而需逐级追索。只能由派发了下级 sub agent 的角色调用（主 agent 或任意层级的 sub agent）。
## 机制前提

- Task 工具返回的 task_id = subagent 的 session id（格式 `ses_xxx`），两者同一。
- sub agent 派发时在 opencode.db 的 session 表建记录（`parent_id`=父session, `agent`=subagent类型, `title`="任务描述 (@agent subagent)"），消息实时落 message/part 表。
- task_id 持久化在数据库，重启 opencode 不丢，中断后可查回。
- agent 不知道自己的 session id（系统提示/环境变量均不提供），所以 skill 靠**任务名称匹配**定位，不依赖 agent 提供 id。
- `opencode session list` 默认只列顶层 session（parent_id IS NULL），看不到 sub agent，必须查库。
- 数据库路径默认 `~/.local/share/opencode/opencode.db`，用 `opencode db path` 确认。

## 使用流程

### 1. 按任务名称查询 sub agent 的 task_id

传入派发时写的任务描述关键词：

```bash
python "<skill_dir>/scripts/resume.py" --name "任务名称关键词"
```

脚本全局匹配 `session.title LIKE '%关键词%' AND parent_id IS NOT NULL`，返回所有匹配的 sub agent（含 task_id、中断状态、parent 信息）。

排查某父会话的全部下级（需已知父 session id）：

```bash
python "<skill_dir>/scripts/resume.py" --session ses_xxxxx
```

输出 JSON：`matches` 数组，每条含 `task_id`、`title`、`agent`、`parent_id`、`parent_title`、`msg_count`、`last_finish`、`task_state`、`task_result_empty`、`interrupted`。

### 2. 识别中断的 sub agent

中断信号（`interrupted=true` 或综合判断）：
- `last_finish` 非 `stop`（`unknown`/`error`/`length`/`content_filter`/`tool_calls` 均为异常；正常完成是 `stop`）
- `task_result_empty=true`（Task 工具返回空结果）
- 消息数明显过少且无产出

`interrupted=null` 表示不确定，看 `last_finish` 和 `task_result_empty` 判断。

多结果时看 `parent_title` 确认是不是自己派发的那个（避免跨会话同名误匹配）。

### 3. 用 Task 工具接续

对中断 sub agent，调 Task 工具时：
- `task_id` = 脚本输出的 task_id（`ses_xxx`）
- `subagent_type` 用与原 sub agent 匹配的类型；若原类型不在当前 available，用 `general`
- prompt 写明："接续上次会话。上次任务：<title>。已完成：<据产出文件判断>。下一步：<待续>。不要重做已完成步骤。"

接续前先用 Glob/Read 检查预期产出文件，区分"真中断"与"空返回但文件已写入"（后者无需接续，补登记即可）。

## 多级 sub agent 逐级接续

本 skill 天然支持多级，无需特殊配置：

1. 主 agent 调本 skill，传入 sub-A 的任务名称 -> 拿到 sub-A 的 task_id -> 用 Task 工具接续 sub-A
2. sub-A 恢复运行后，若发现自己因下级 sub-sub-B 中断 -> sub-A 调本 skill，传入 sub-sub-B 的任务名称 -> 拿到 sub-sub-B 的 task_id -> 接续
3. 逐级追索，逐级接续，直到叶子节点

每级调用方式完全一样：传入下级的任务名称，skill 返回 task_id。主 agent 和 sub agent 无需知道自己 id，也无需区分层级。

## 注意事项

- 只能由"派发了下级 sub agent"的角色调用；叶子节点无意义。
- 脚本只读查库（`mode=ro`），不写入，安全。
- 任务名称匹配是模糊的（LIKE %name%），多结果时看 parent_title 确认。
- 接续 prompt 要明确：若仅验证上下文连续性，写"只回答不操作"；若继续执行，写清已完成步骤避免重做。
- 弱模型（如 deepseek-v4-flash）可能不完全听从 prompt 限制，接续时注意监控产出。
- 跨父会话恢复（当前会话恢复别的父会话的 sub agent）可行性依 opencode 版本，实测确认。
