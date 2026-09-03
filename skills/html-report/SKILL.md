---
name: html-report
description: 智能HTML报告渲染引擎。输入为自然Markdown内容，引擎自动分析内容结构、识别可视化模式、匹配叙事组件，输出单文件自包含HTML。支持20种原子组件、SVG流程图/数据图表、5套色板、暗色模式、海报布局。当需要生成HTML报告/文档/页面/海报时触发。
---

# html-report

智能HTML报告渲染引擎。

## 核心设计

```
agent输入：自然Markdown（标题、段落、列表、表格、引用、代码块）
    ↓
skill执行：
  1. 分块（按标题/段落/表格/列表切分内容单元）
  2. 模式识别（分析每个内容单元的结构特征）
  3. 组件匹配（识别到的模式 → 对应可视化组件）
  4. 渲染（组件HTML / 普通Markdown HTML）
  5. 组装（合并为完整HTML骨架 + 内联CSS + 暗色模式）
    ↓
输出：单文件自包含HTML（零外部依赖，file://可直接打开）
```

**agent不写任何标记、不知道任何组件。** 所有结构分析和可视化决策由skill完成。

## 输入

- **content**：Markdown格式的报告正文（纯内容，无组件标记）
- **theme**：blue-orange / purple-green / warm-paper / vintage-tech / poster-vintage（默认blue-orange）
- **layout**：article（默认，单栏文章）/ tufte（边栏学术）/ poster（复古海报，仅 poster-vintage 主题）
- **title**：报告标题

## 渲染流程（执行指令）

### Step 1：内容分块

将Markdown正文切分为独立的内容单元：
- **章节块**：以 `#`/`##`/`###` 开头的标题及其后续段落，直到下一个同级/更高级标题
- **表格块**：连续的 `|` 行
- **列表块**：连续的 `-` / `*` / `1.` 行
- **引用块**：连续的 `>` 行
- **代码块**：``` 包裹的块
- **独立段落**：单个 `<p>`

### Step 2：模式识别

对每个内容单元，按以下优先级检查是否匹配组件模式：

#### P1. 时间线模式
**触发条件**：列表项以日期/年份/时间（如"2024-01"、"2023年"、"Q1"）开头，后面跟事件描述
**特征**：连续3+个时间序列条目，有时间递进关系
**示例**：
```markdown
- 2023年：纯文本时代，LLM输出Markdown
- 2024年：模板美化时代，html-anything出现
- 2025年：交互式探索时代，Quarto支持自包含HTML
- 2026年：领域原生时代，需求清晰化
```

#### P2. 对比模式
**触发条件**：
- 表格只有2-3列，且表头暗示对比（如"维度/A/B"、"特性/方案1/方案2"）
- 段落中出现 "vs"、"对比"、"A vs B"、"相比" 等关键词
- 列表中有明确的 "优势/短板"、"优点/缺点" 成对出现
**特征**：并列展示两个对象的差异

#### P3. 矛盾模式
**触发条件**：
- 段落中出现 "争议"、"矛盾"、"冲突"、"分歧"、"对立"、"不同观点" 等词
- 列表中有 "立场A/立场B"、"支持/反对" 成对结构
- 引用块中包含 "vs" 或 "but" 连接的对立观点
**特征**：两个来源/观点的直接冲突，不裁决只暴露

#### P4. 概念讲解模式
**触发条件**：
- 段落结构为三段式："它是什么" / "为什么要分" / "怎么用" 或类似变体
- 出现 "痛点"、"是什么"、"怎么工作"、"为什么"、"怎么用" 等标志性短语
- 对单一术语进行系统性解释
**特征**：向非专业读者解释一个概念

#### P5. 数据模式
**触发条件**：
- 列表项主要是数字+标签（如"87% 市场占有率"）
- 段落中包含大量百分比、数值对比
- 表格中数字列占主导
**特征**：可被可视化的数值信息

#### P6. 证据链模式
**触发条件**：
- 列表或段落呈现 "来源 → 引用 → 推理 → 结论" 的递进结构
- 明确标注了引文、出处、推导步骤
**特征**：从原始来源到最终结论的推理路径

#### P7. 缺口模式
**触发条件**：
- 内容中出现 "待补"、"缺口"、"盲区"、"未验证"、"假设"、"未来工作"、"局限性" 等词
- 单源结论（只有一个来源支撑）
**特征**：需要后续补充的信息

#### P8. 步骤模式
**触发条件**：
- 有序列表，项数为 "1. 2. 3." 的连续步骤
- 包含 "检查清单"、"TODO"、"第一步/第二步" 等结构
**特征**：行动指南的分步操作

#### P9. 发现/结论模式
**触发条件**：
- 段落以结论性语句开头（"结论是"、"我们发现"、"实验表明"）
- 包含置信度暗示（"高度确信"、"可能"、"尚不确定"）
- 有证据支撑和缺口标注
**特征**：调研的核心发现

### Step 3：组件渲染

匹配到模式后，从 `references/components.md` 读取对应组件的HTML模板和CSS，将内容数据注入模板生成具体HTML。

**数据提取规则**：
- 从Markdown结构中自动提取字段（日期、标题、描述、数值、来源等）
- 置信度自动推断：关键词"确定/证实/实验"→H，"可能/倾向/观察"→M，"假设/推测/单源"→L
- 来源自动提取：链接文字、引用标记、标注的作者标题

### Step 4：普通Markdown渲染

未匹配到任何模式的内容单元，按标准Markdown渲染为HTML：
- 标题 → `<h1>`~`<h6>`
- 段落 → `<p>`
- 列表 → `<ul>`/`<ol>`
- 引用 → `<blockquote>`
- 代码 → `<pre><code>`
- 表格 → `<table>`
- 粗体/斜体/链接 → 正常转换

### Step 5：组装HTML骨架

**海报布局特殊处理（layout=poster）：**
- 标题区：从 Markdown 第一个 `#` 提取标题，第一个 `##` 提取副标题，首段作为引导文
- 内容分区：将内容块分配到 `.poster-main`（主内容）和 `.poster-sidebar`（侧栏）
  - 侧栏内容标识：引用块 `>` 或标注为侧栏的段落
  - 其余内容进入主区域
- 所有主内容块自动包裹在 `<div class="poster-card">` 中
- 排行数据（表格/数值列表）→ `rank-list` 组件
- 带图标的说明列表 → `poster-icon-row` 组件
- 注意事项段落 → `poster-alert` 组件

```html
<!DOCTYPE html>
<html lang="zh-CN" data-theme="{theme}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  /* 色板变量 */
  /* 排版参数（poster-vintage 有额外覆盖） */
  /* 布局CSS（article / tufte / poster） */
  /* 组件CSS（仅注入实际用到的） */
  /* 暗色模式 */
</style>
</head>
<body>
  <!-- 暗色切换按钮 -->
  <!-- layout=poster 时 -->
  <div class="report-body poster">
    <header class="poster-header">
      <h1>{title}</h1>
      <div class="poster-subtitle">{subtitle}</div>
      <div class="poster-lead">{lead}</div>
    </header>
    <div class="poster-main">
      <!-- 主内容：poster-card 包裹的内容块 -->
    </div>
    <aside class="poster-sidebar">
      <!-- 侧栏：poster-sidebar-item -->
    </aside>
  </div>
  <!-- layout=article 时 -->
  <div class="report-body">
    <!-- 内容按顺序排列 -->
  </div>
  <!-- layout=tufte 时 -->
  <div class="report-body tufte">
    <!-- 内容按顺序排列 -->
  </div>
  <script>/* 暗色模式脚本 */</script>
</body>
</html>
```

### Step 6：样式注入

1. 从 `references/themes.md` 读取选中色板的CSS变量
2. 读取排版参数、间距Token
3. 读取暗色模式变体
4. **仅注入实际用到的组件CSS**（未匹配的组件不注入）
5. 合并为一个 `<style>` 块

### Step 7：质量检查

- [ ] 单文件自包含（`file://`可打开）
- [ ] 暗色模式可切换
- [ ] 移动端正常
- [ ] 打印/PDF可用
- [ ] CSS变量引用色板（无硬编码色值）
- [ ] 组件渲染后的HTML结构完整

## 模式匹配优先级

当一块内容可能匹配多个模式时，按以下优先级决定：

1. **矛盾模式**（P3）> **对比模式**（P2）——有"争议/冲突"关键词时优先矛盾
2. **时间线模式**（P1）> **步骤模式**（P8）——有日期时间时优先时间线
3. **数据模式**（P5）> **发现模式**（P9）——大量数字时优先可视化
4. **概念模式**（P4）优先于普通段落——三段式讲解总是渲染为概念卡

## 组件库

见 `references/components.md`，包含14个组件：

**叙事组件**：timeline-item · card-comparison · conflict-view · concept-card · step-card · card-finding
**数据组件**：kpi-card · chart · diagram
**结构组件**：evidence-chain · gap-box · source-tag · badge-confidence · toc-nav
**海报组件**：rank-list · poster-card · poster-sidebar-item · poster-divider · poster-icon-row · poster-alert

每个组件包含：触发条件 + 数据提取规则 + HTML模板 + CSS。

## 色板与排版

见 `references/themes.md`。

- 5套色板：blue-orange / purple-green / warm-paper / vintage-tech / poster-vintage
- 暗色模式：每套色板配dark变体
- 排版：正文17px、行高1.6、行长42em（poster-vintage 覆盖为16px/1.55/衬线体）
- 布局：单栏居中（默认）/ Tufte边栏（可选）/ 海报布局（poster-vintage 专用）

## 资源文件

| 路径 | 用途 |
|------|------|
| references/components.md | 组件触发条件+数据提取规则+HTML模板+CSS |
| references/themes.md | 色板+排版+间距Token+暗色模式 |
| assets/*.html | HTML样例（风格参考，skill不读取） |

## 核心规则

1. **agent不写任何标记**。agent只输出自然Markdown，skill负责全部结构分析和可视化。
2. **skill是智能引擎**。不是模板填充器，而是内容感知型渲染器。
3. **组件对agent不可见**。agent不需要知道组件存在，不需要学习组件语法。
4. **组件增减只改skill**。新增组件只需更新skill的components.md，agent完全无感知。
5. **模式识别可覆盖**。如果某块内容被错误匹配，可通过内容结构调整来引导（如改变措辞、调整结构）。
