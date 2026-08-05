---
name: html-report
description: 智能HTML报告渲染引擎。支持 research/editorial 双模式，输入自然 Markdown，自动进行可选结构增强、语义分块、组件匹配，输出单文件自包含 HTML。适合调研报告、趋势解读、知识长文、公众号风格文章。
trigger: 用户需要将 Markdown 报告/文章渲染成 HTML，或要求视觉化、叙事化、杂志风、公众号长图文风格的报告。
---

# html-report

智能 HTML 报告渲染引擎，支持两种工作模式：

- **research 模式**：适合调研、审计、证据链报告。使用 timeline/chain/gap-box/step-card/chart/diagram 等研究组件。
- **editorial 模式**：适合趋势解读、知识长文、公众号风格文章。使用 hero-cover/section-hero/card/comparison/highlight/quote 等编辑式组件。

## 核心设计

```
agent 输入：自然 Markdown + 参数
    ↓
Step 0：意图解析（mode / theme / density）
    ↓
Step 1：结构增强预检（标记需结构优化的章节）
    ↓
Step 2（可选）：结构增强（仅 editorial + narrative=true，形式转换不补内容）
    ↓
Step 3：语义分块（按标题/段落/表格/列表/引用切分）
    ↓
Step 4：语义识别（这段内容想表达什么）
    ↓
Step 5：组件选择（语义 → 组件 → 变体）
    ↓
Step 6：渲染（读取 themes.md / components.md，注入 CSS）
    ↓
Step 7：质量检查（工程检查）
    ↓
输出：单文件自包含 HTML
```

**agent 不写任何组件标记。** 所有结构分析、组件选择、视觉决策由 skill 完成。

## 职责边界

html-report 只负责把已有 Markdown 渲染为 HTML。禁止承担以下职责：

- 禁止读取调研项目资产来决定报告内容
- 禁止选择报告业务模板
- 禁止判断用户报告意图
- 禁止生成报告正文
- 禁止补造 raw、采录、分析或知识包
- **禁止做内容改写**（补讲解、补事实、补前因后果）——这是报告 agent 的职责

## 输入参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `content` | string | 必填 | Markdown 格式正文 |
| `title` | string | 自动提取 | 报告标题 |
| `mode` | string | `research` | `research` / `editorial` |
| `theme` | string | `editorial-warm`（editorial）/ `blue-orange`（research） | 主题 |
| `narrative` | boolean | `true`（editorial）/ `false`（research） | 是否启用结构增强 |
| `density` | string | `normal` | `low` / `normal` / `high`，控制视觉密度 |
| `enable_confidence_badge` | boolean | `false` | 是否渲染置信度徽章。仅当显式传入 true 或 Markdown 已含置信度标记时渲染 |

## 渲染流程

### Step 0：意图解析

根据 `mode` 决定渲染策略：

- `mode=research`：使用研究/审计组件（timeline、chain--evidence、gap-box、step-card、chart、diagram 等），不启用结构增强。
- `mode=editorial`：使用编辑式组件（hero-cover、section-hero、card、comparison、highlight、quote 等），默认启用结构增强。

### Step 1：结构增强预检

在进入结构增强前，对每个章节块逐段做结构评估，标记需要结构优化的段落。**此步骤在 editorial + narrative=true 时为必做**，research 模式可跳过。

**评估维度**：

| 维度 | 检查问题 | 不达标信号 |
|---|---|---|
| 结构完整性 | 章节是否有引导句和收束句？ | 只有一句话的 H3、纯 bullet 无过渡句 |
| 信息密度 | 是否高密度 bullet 堆积？ | 连续 3+ 个 bullet 项无连接段落、纯名词短语罗列 |
| 组件适配 | bullet 适合组件化吗？ | 可识别为 list/comparison/highlight 等组件的结构 |

**标记规则**：
- 结构不完整或信息密度过高 → 标记该段落为 `needs-enhance`，进入 Step 2 强制结构增强。
- 结构完整 → 标记为 `ok`，Step 2 可跳过。
- 标记结果随章节块一起传递到 Step 2。

### Step 2：结构增强（可选，editorial + narrative=true）

当 `narrative=true` 时，对源 Markdown 做**形式转换**（不是内容改写）：

1. 把密集 bullet list 改写成 1-2 段连贯文字，保留关键数据、来源、引用。
2. 识别适合组件化的结构并保留为语义块：
   - 两个对照的列表/表格 → 保留为对比块
   - 连续步骤/因果链 → 保留为列表/链式块
   - 数字指标 → 保留为高亮块
   - 引用/金句 → 保留为引用块
3. 不增删事实，不编造数据，改写后内容可溯源。

**安全规则（关键）**：

- bullet→段落时，只做**形式转换**：用句号/逗号替换 bullet 符号，保留原文用词和语序。
- **不得增删任何事实、数据、来源。**
- **不得补讲解性文字**——这是内容改写，属于报告 agent 职责。
- 如果原文是提纲，skill 的输出就是"形式转换后的提纲"——不负责讲清楚，只负责结构清晰。
- 保留所有数字、百分比、金额、时间、来源。
- 不替换专业术语，不加入原文没有的观点。

### Step 3：语义分块

将 Markdown 切分为独立内容单元：

- **封面块**：文档开头到第一个 H2 之前的内容
- **章节块**：每个 H2 标题及其后续内容直到下一个 H2
- **表格块**：连续的 `|` 行
- **列表块**：连续的 `-` / `*` / `1.` / `i.` 行
- **引用块**：连续的 `>` 行
- **独立段落**：单个 `<p>`

### Step 4：语义识别

对每个内容单元，按以下优先级判断语义意图：

| 语义 | 判断依据 |
|---|---|
| 封面 | 文档开头、包含 H1 或标题参数 |
| 章节入口 | H2 标题 |
| 子主题/概念 | H3 标题 + 后续段落/列表 |
| 对比 | 表格 2-3 列含 A/B、段落含"vs/对比/相比"、成对列表 |
| 冲突 | 含"争议/矛盾/冲突/分歧"或"立场A/立场B" |
| 步骤/因果链 | 有序列表、含"导致/从而/于是/→"、标题含"流程/闭环/链条" |
| 数据/结论 | 大量数字、百分比、结论性语句 |
| 引用/金句 | blockquote、短句强调 |
| 缺口/盲区 | 含"待补/缺口/盲区/未验证/假设/局限性" |
| 时间线 | 列表项以日期/年份开头 |
| 概念讲解 | 段落结构为三段式："痛点/是什么/怎么工作"或类似变体 |

### Step 5：组件选择

先按语义选组件，再按语义角色和位置选变体：

```
语义 → 组件 → 变体

封面                → hero-cover
H2 章节             → section-hero + section-badge
H3 子主题           → card
  ├─ 定义/核心/能力/价值/优势/案例 → card--accent
  ├─ 局限/风险/挑战/反面         → card--secondary
  ├─ 注意/提示/总结              → card--top-accent
  ├─ 普通补充说明                → card--plain
  └─ 概念讲解三段式               → card--concept

对比                → comparison
  ├─ 普通两方对照    → comparison--contrast
  └─ 争议/冲突       → comparison--conflict

列表                → list
  ├─ 普通并列        → list--bullet
  ├─ 行动步骤        → list--decimal
  ├─ 叙事要点/步骤   → list--roman
  └─ 因果递进        → list--chain

数据/结论            → highlight
  ├─ 多个指标        → highlight--kpi
  ├─ 单点大数据      → highlight--stat
  └─ 结论重音        → highlight--closing

引用                → quote
  ├─ 短金句          → quote--pullquote
  └─ 长引用/证据     → quote--block

来源                → source-footer
table              → table（加 .table-wrap）
时间序列            → timeline
证据推理            → chain--evidence
因果递进            → chain--process
缺口/盲区           → gap-box
置信度              → badge-confidence（仅 enable_confidence_badge=true 时）
步骤流程            → step-card
数据图表            → chart
流程图/架构图       → diagram
```

### Step 6：渲染

1. 从 `references/themes.md` 读取选中主题的 CSS 变量。
2. 从 `references/components.md` 读取实际用到的组件 CSS。
3. 组装 HTML 骨架，合并为一个 `<style>` 块。
4. 注入暗色模式切换脚本。

### Step 7：质量检查

**工程检查（only）**：

- [ ] 单文件自包含（`file://` 可直接打开）
- [ ] 暗色模式可切换
- [ ] 移动端正常
- [ ] 打印/PDF 可用
- [ ] CSS 变量引用色板，无硬编码色值
- [ ] 结构增强后的事实、数据、来源无丢失
- [ ] 组件选择失败时有安全回退（渲染为段落/列表/表格）

**不设叙事性专项自检**——全局 skill 不做内容改写，无需叙事自检。

## 模式匹配优先级

当一块内容可能匹配多个模式时，按以下优先级决定：

1. **封面** > **章节入口** ——文档开头优先封面，H2 优先章节入口
2. **冲突** > **对比** ——有"争议/冲突"关键词时优先冲突
3. **时间线** > **步骤** ——有日期时间时优先时间线
4. **数据/结论** > **普通段落** ——大量数字时优先可视化
5. **概念讲解** > **普通段落** ——三段式讲解总是渲染为概念卡
6. **证据推理** > **因果递进** ——含"来源/引用/推理/结论"优先证据链

## 组件决策速查

| 当你看到这种内容 | 选这个组件 | 变体依据 |
|---|---|---|
| 报告标题 + 引言 | hero-cover | 文档开头 |
| H2 章节标题 | section-hero | 右上角章节标从标题关键词推断 |
| H3 子标题 + 段落 | card | 标题关键词决定 accent/secondary/top/plain/concept |
| 两方对照 | comparison | 含"冲突/争议"→ conflict，否则 contrast |
| 步骤、清单 | list | 数字步骤→decimal，叙事步骤→roman，因果→chain |
| 数字指标 | highlight | 多指标→kpi，单数据→stat，结论句→closing |
| 引用、金句 | quote | 短句强调→pullquote，长引用→block |
| 表格 | table | 一律加 .table-wrap |
| 来源标注 | source-footer | 文末或卡片底部 |
| 时间序列 | timeline | 日期/年份开头 |
| 证据链 | chain--evidence | 来源→引用→推理→结论 |
| 因果链 | chain--process | 递进/因果词 |
| 缺口/盲区 | gap-box | 待补/未验证/假设 |
| 步骤操作 | step-card | 有序步骤 + 检查清单 |
| 数据图表 | chart | 数值数据可可视化 |
| 流程图 | diagram | 流程/架构/拓扑 |

## 组件库

见 `references/components.md`，包含 17 个组件：

**编辑式组件**：hero-cover · section-hero · card（5 变体）· list（4 变体）· comparison（2 变体）· highlight（3 变体）· quote（2 变体）· source-footer
**研究组件**：timeline · chain（2 变体）· gap-box · badge-confidence · step-card · toc-nav · diagram · chart
**通用组件**：table

每个组件包含：触发条件 + 数据提取规则 + HTML 模板 + CSS。

## 色板与排版

见 `references/themes.md`。

- 4 套色板：editorial-warm（编辑式暖纸媒）/ blue-orange（技术调研）/ purple-green（商业决策）/ warm-paper（文史知识创作）
- 暗色模式：每套色板配 dark 变体
- 排版：正文 17px、行高 1.85、行长 42em
- 布局：单栏居中（默认）/ Tufte 边栏（可选）

## 资源文件

| 路径 | 用途 |
|---|---|
| references/components.md | 组件触发条件+数据提取规则+HTML模板+CSS |
| references/themes.md | 色板+排版+间距Token+暗色模式 |

## 核心规则

1. **agent 不写任何标记。** agent 只输出自然 Markdown，skill 负责全部结构分析和可视化。
2. **skill 是智能引擎。** 不是模板填充器，而是内容感知型渲染器。
3. **组件对 agent 不可见。** agent 不需要知道组件存在，不需要学习组件语法。
4. **组件增减只改 skill。** 新增组件只需更新 skill 的 components.md，agent 完全无感知。
5. **语义优先于视觉。** 先判断内容意图，再决定视觉变体。
6. **默认安全回退。** 当无法确定组件时，回到段落、列表、表格等默认渲染。
7. **事实不可丢失。** 结构增强必须保留所有关键数据、来源、引用。
8. **不做内容改写。** 结构增强只做形式转换（bullet→段落），不补讲解、不补事实、不补前因后果。
9. **不做业务编排。** 报告类型、读者定位、证据呈现策略、模板选择均由报告 agent 决定。
10. **默认不显示内部置信度。** 不得自动把"确定/可能/假设"等普通文字转成 H/M/L 徽章。仅 `enable_confidence_badge=true` 时渲染。

## 使用示例

### 示例 1：编辑式趋势报告

```markdown
<!-- mode: editorial -->
<!-- theme: editorial-warm -->

# 2026知识管理趋势

> 当AI接管了运算，人类的核心竞争力还剩什么？

## 引言：从「冷存储」到「活资产」

过去十年，企业知识管理其实只做了一件事：建仓库。
...

## 一、AI原生知识库

### 定义

AI原生知识库不是更聪明的搜索插件，而是围绕AI能力重新设计的系统。

### 核心能力

- 智能聚合：20+格式自动采集
- 场景服务：自然语言问答
- 持续进化：自动识别知识缺口
```

### 示例 2：调研报告（research 模式）

```markdown
<!-- mode: research -->

## 结论

我们发现，AI原生知识库能显著降低检索耗时。

## 证据

- 来源：Gartner 2025 报告
- 引用："企业知识复用率不足 30%"
- 推理：传统搜索依赖关键词，AI 语义检索更精准
- 结论：检索耗时从 15 分钟降至 2 分钟以内
```
