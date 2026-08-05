# html-report 组件库

> 所有组件：零外部依赖 · CSS 变量引用色板 · 响应式 · 打印友好。
> agent 不写任何组件标记，skill 通过语义识别自动匹配组件与变体。

---

## 0. 公共工具类

```css
.accent-line {
  width: 60px;
  height: 3px;
  background: var(--color-accent);
  margin: 1rem 0;
}
.table-wrap { overflow-x: auto; }
```

---

## 1. hero-cover

**用途**：报告封面。包含小字标、大标题、短装饰线、副标题/引言、来源注。

**触发条件**：
- 文档第一个内容块；或
- 显式标题参数 `title` + 引言/副标题；或
- Markdown 中 H1 标题及其后第一个引用块/段落。

**数据提取**：
- `label`：可选，如"报告"
- `title`：报告主标题
- `subtitle`：副标题或引言
- `source`：来源 URL 或说明

**HTML 模板**：

```html
<header class="hero-cover">
  <div class="hero-cover__label">报告</div>
  <h1 class="hero-cover__title">主标题</h1>
  <div class="accent-line" style="margin-left:auto;margin-right:auto;"></div>
  <blockquote class="quote quote--pullquote">引言或副标题</blockquote>
  <div class="source-footer">来源：xxx</div>
</header>
```

```css
.hero-cover {
  max-width: var(--max-width-body);
  margin: 0 auto;
  padding: 5rem 1.5rem 3rem;
  text-align: center;
}
.hero-cover__label {
  font-size: 0.75rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}
.hero-cover__title {
  font-size: 2.6rem;
  line-height: 1.2;
  margin: 0.5rem 0 1.2rem;
}
.hero-cover__subtitle {
  font-size: 1.15rem;
  color: var(--color-text-secondary);
}
```

---

## 2. section-hero

**用途**：章节入口。包含右上角章节标、大标题、装饰线、可选副标题。

**触发条件**：H2 标题及其后续 1-2 个段落。

**数据提取**：
- `label`：从 H2 内容推断，如"趋势一""引言"
- `title`：H2 文本
- `subtitle`：H2 后第一个非列表、非引用的段落（如为解释性语句）

**HTML 模板**：

```html
<section class="section" id="section-anchor">
  <div class="section__header">
    <span class="section__label">趋势一</span>
    <h2 class="section__title">标题</h2>
    <div class="accent-line"></div>
  </div>
  ...
</section>
```

```css
.section {
  margin-bottom: var(--space-2xl);
  position: relative;
}
.section__label {
  position: absolute;
  top: 0;
  right: 0;
  font-size: 0.75rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--color-text-muted);
}
.section__title {
  font-size: 2rem;
  margin-bottom: 0.8rem;
  padding-right: 5rem;
}
@media (max-width: 720px) {
  .section__title { padding-right: 0; font-size: 1.7rem; }
  .section__label { position: static; display: block; margin-bottom: 0.5rem; }
}
```

---

## 3. card

**用途**：子主题、概念、定义、案例、要点容器。

**触发条件**：
- H3 标题 + 后续段落/列表；或
- 连续段落中表达单一概念；或
- 概念讲解三段式（痛点/是什么/怎么工作）→ 变体 `concept`

**变体**：
- `card--accent`：赭石左框（主强调、定义、核心能力）
- `card--secondary`：墨绿左框（反面、局限、风险、对比项）
- `card--top-accent`：赭石顶框（轻量强调）
- `card--plain`：无边框，仅浅色背景
- `card--concept`：三段式概念卡（继承 card 样式）

**变体选择规则**：
- 标题含"定义/核心/能力/价值/优势/案例" → `accent`
- 标题含"局限/风险/挑战/反面/对比项" → `secondary`
- 标题含"注意/提示/总结" → `top-accent`
- 普通补充说明 → `plain`
- 概念讲解三段式（痛点/是什么/怎么工作）→ `concept`

**HTML 模板**：

```html
<div class="card card--accent">
  <h3>标题</h3>
  <p>内容</p>
</div>
```

```css
.card {
  background: var(--color-bg-soft);
  padding: 1.25rem;
  margin: 1.5rem 0;
}
.card--accent { border-left: 3px solid var(--color-accent); }
.card--secondary { border-left: 3px solid var(--color-secondary); }
.card--top-accent { border-top: 3px solid var(--color-accent); }
.card--plain { background: var(--color-bg-soft); }

.card h3, .card h4 {
  margin: 0 0 0.5rem;
  color: var(--color-text);
}
.card--accent h3, .card--accent h4 { color: var(--color-accent); }
.card--secondary h3, .card--secondary h4 { color: var(--color-secondary); }
.card--top-accent h3, .card--top-accent h4 { color: var(--color-accent); }

.card p {
  color: var(--color-text-secondary);
  margin: 0.4rem 0 0;
}
```

### 3.1 concept 变体

三段式概念卡，继承 card 样式。从 Markdown 结构识别（P4 概念讲解模式），不依赖知识包。

```html
<div class="card card--concept">
  <h3>概念名称</h3>
  <div class="card__section card__section--pain">
    <div class="card__section-label">痛点</div>
    <p>...</p>
  </div>
  <div class="card__section card__section--what">
    <div class="card__section-label">是什么</div>
    <p>...</p>
  </div>
  <div class="card__section card__section--how">
    <div class="card__section-label">怎么工作</div>
    <p>...</p>
  </div>
</div>
```

```css
.card__section {
  margin-top: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius);
}
.card__section--pain { border-left: 3px solid var(--color-danger); background: rgba(185,86,63,0.06); }
.card__section--what { border-left: 3px solid var(--color-primary); background: var(--color-bg-muted); }
.card__section--how { border-left: 3px solid var(--color-success); background: rgba(47,94,78,0.06); }
.card__section-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}
```

---

## 4. list

**用途**：并列要点、步骤、流程。

**触发条件**：Markdown 列表。

**变体**：
- `list--bullet`：普通无序列表（默认）
- `list--decimal`：有序步骤、行动清单
- `list--roman`：叙事性步骤、并列要点（杂志风格）
- `list--chain`：因果递进链，带箭头

**变体选择规则**：
- 列表项以数字 `1.` 开头，含"第一步/检查清单/TODO" → `decimal`
- 列表项以 `i. ii. iii.` 开头，或语义为"并列维度/叙事要点" → `roman`
- 列表项含"导致/从而/于是/→"等因果词，或标题含"闭环/链条/流程" → `chain`
- 其他 → `bullet`

**HTML 模板**：

```html
<ul class="list list--bullet">
  <li>...</li>
</ul>

<ol class="list list--roman">
  <li><strong>标题</strong><p>说明</p></li>
</ol>

<ol class="list list--chain">
  <li>第一步</li>
  <li>第二步</li>
  <li class="list__highlight">最终结果</li>
</ol>
```

```css
.list { margin: 1rem 0; padding-left: 1.6rem; }
.list li { margin: 0.5rem 0; color: var(--color-text-secondary); }
.list--bullet li::marker { color: var(--color-accent); }

.list--roman {
  list-style: lower-roman;
  padding-left: 2rem;
  color: var(--color-accent);
}
.list--roman li > strong { color: var(--color-text); }
.list--roman li > p { margin: 0.2rem 0 0; }

.list--decimal { list-style: decimal; }
.list--decimal li::marker { color: var(--color-accent); font-weight: 700; }

.list--chain {
  list-style: none;
  padding: 0;
}
.list--chain li {
  position: relative;
  padding-left: 2rem;
  margin-bottom: 0.75rem;
  font-size: 1.05rem;
}
.list--chain li::before {
  content: "→";
  position: absolute;
  left: 0;
  color: var(--color-accent);
  font-weight: 700;
}
.list--chain .list__highlight {
  color: var(--color-accent);
  font-size: 1.2rem;
  font-weight: 700;
}
```

---

## 5. comparison

**用途**：两方对照。可表达对比、优劣、矛盾冲突。

**触发条件**：
- 表格只有 2-3 列，表头含"维度/A/B""优势/短板""价值/局限"
- 段落中含"vs、对比、相比、不是…而是…"
- 列表成对出现"立场A/立场B""支持/反对"
- 出现"争议、矛盾、冲突、分歧" → 变体 `conflict`

**变体**：
- `comparison--contrast`：普通双栏对比
- `comparison--conflict`：中间加入"分歧焦点"

**变体选择规则**：
- 含"争议/矛盾/冲突/分歧" → `conflict`
- 其他两方对照 → `contrast`

**HTML 模板**：

```html
<div class="comparison comparison--contrast">
  <div class="comparison__side comparison__side--a">
    <h4>旧范式</h4>
    <p>...</p>
  </div>
  <div class="comparison__side comparison__side--b">
    <h4>新范式</h4>
    <p>...</p>
  </div>
</div>
```

```css
.comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  margin: 1.5rem 0;
}
.comparison__side {
  background: var(--color-bg-soft);
  padding: 1.25rem;
  border-top: 3px solid var(--color-secondary);
}
.comparison__side--b { border-top-color: var(--color-accent); }
.comparison__side h4 {
  margin: 0 0 0.6rem;
  color: var(--color-secondary);
}
.comparison__side--b h4 { color: var(--color-accent); }
.comparison__side p { color: var(--color-text-secondary); margin: 0; }

.comparison--conflict {
  grid-template-columns: 1fr auto 1fr;
  gap: 0.75rem;
}
.comparison__focal {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 80px;
  padding: 0.5rem;
}
.comparison__focal-label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-warning);
  margin-bottom: 0.25rem;
}
.comparison__focal-text {
  font-size: 0.8rem;
  color: var(--color-text);
  text-align: center;
  writing-mode: vertical-rl;
}
@media (max-width: 720px) {
  .comparison,
  .comparison--conflict { grid-template-columns: 1fr; }
  .comparison__focal { display: none; }
}
```

---

## 6. highlight

**用途**：数据、指标、结论重音。

**触发条件**：
- 列表项为"数字 + 标签"
- 段落中突出显示的关键数字
- 章节末尾的结论性语句
- 标题含"结论是/我们发现/实验表明"

**变体**：
- `highlight--kpi`：多个指标网格（KPI 卡）
- `highlight--stat`：单点大数据 + 说明（左框）
- `highlight--closing`：大号结论句（左框）

**变体选择规则**：
- 连续 3+ 个"数字+标签" → `kpi`
- 单个数字 + 长说明段落 → `stat`
- 章节末尾结论句，或含"因此/所以/结论是" → `closing`

**HTML 模板**：

```html
<div class="highlight highlight--stat">
  <div class="highlight__number">85%</div>
  <div class="highlight__caption">企业知识库沦为死库</div>
</div>

<div class="highlight highlight--kpi">
  <div class="highlight__kpi"><div class="highlight__value">3月→1月</div><div class="highlight__label">上手时间</div></div>
  ...
</div>

<div class="highlight highlight--closing">
  这不是工具的升级，而是知识从成本中心走向价值中心的质变。
</div>
```

```css
.highlight {
  margin: 1.5rem 0;
}
.highlight--stat {
  background: var(--color-bg-soft);
  border-left: 3px solid var(--color-accent);
  padding: 1.25rem;
}
.highlight__number {
  font-size: 2.4rem;
  font-weight: 700;
  color: var(--color-accent);
  line-height: 1;
}
.highlight__caption {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  margin-top: 0.5rem;
}

.highlight--kpi {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 1rem;
}
.highlight__kpi {
  text-align: center;
  padding: 1rem;
  background: var(--color-bg-soft);
}
.highlight__value {
  font-size: 1.7rem;
  font-weight: 700;
  color: var(--color-accent);
  line-height: 1;
}
.highlight__label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  margin-top: 0.45rem;
}

.highlight--closing {
  border-left: 3px solid var(--color-accent);
  padding: 1.25rem 0 1.25rem 1.5rem;
  color: var(--color-accent);
  font-size: 1.3rem;
  line-height: 1.55;
  font-weight: 700;
}
```

---

## 7. quote

**用途**：引用、金句、强调。

**触发条件**：
- Markdown 引用块 `>`；或
- 段落中含引号、来源标注；或
- 需要视觉强调的单段文字。

**变体**：
- `quote--pullquote`：左侧色条、强调色文字、较大字号（杂志风格）
- `quote--block`：普通引用，适合长引用或来源引用

**变体选择规则**：
- 引用较短（1-3 句）、无明确来源标注、用于制造节奏 → `pullquote`
- 引用较长、含来源、用于证据 → `block`

**HTML 模板**：

```html
<blockquote class="quote quote--pullquote">
  当AI接管了运算，人类的核心竞争力还剩什么？
</blockquote>
```

```css
.quote {
  margin: 1.5rem 0;
  padding: 0.5rem 0 0.5rem 1.5rem;
  border-left: 3px solid var(--color-border);
  color: var(--color-text-secondary);
}
.quote--pullquote {
  border-left-color: var(--color-accent);
  color: var(--color-accent);
  font-size: 1.2rem;
  line-height: 1.6;
}
.quote--block {
  font-size: 1rem;
}
.quote cite {
  display: block;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-top: 0.5rem;
  font-style: normal;
}
```

---

## 8. source-footer

**用途**：来源标注。可内联或块级。

**触发条件**：
- 文末或卡片底部的"作者 · 标题"
- Markdown 链接 `[标题](URL)` 形式的来源
- 独立成行的来源信息

**HTML 模板**：

```html
<div class="source-footer">来源：微信公众号 · 2026-03-21</div>
```

```css
.source-footer {
  display: inline-block;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  border-left: 2px solid var(--color-accent);
  padding-left: 0.8rem;
  margin-top: 1.5rem;
}
```

---

## 9. table

**用途**：结构化数据展示。

**触发条件**：Markdown 表格。

**HTML 模板**：渲染为 `<table>`，外层加 `.table-wrap`。

```css
.table-wrap { overflow-x: auto; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.2rem 0;
  font-size: 0.85rem;
}
th, td {
  padding: 0.55rem 0.7rem;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: top;
}
th {
  color: var(--color-secondary);
  font-weight: 700;
  border-bottom-width: 2px;
}
tr:last-child td { border-bottom: none; }
```

---

## 10. timeline

**用途**：时间序列。

**触发条件**：列表项以日期/年份/时间开头，连续 3+ 个时间序列条目。

```html
<div class="timeline">
  <div class="timeline__item">
    <div class="timeline__dot"></div>
    <div class="timeline__content">
      <div class="timeline__date">2024-01</div>
      <h5>事件</h5>
      <p>描述</p>
    </div>
  </div>
</div>
```

```css
.timeline {
  position: relative;
  padding-left: 2rem;
  margin: 1rem 0;
}
.timeline::before {
  content: "";
  position: absolute;
  left: 0.55rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}
.timeline__item { position: relative; margin-bottom: 1.25rem; }
.timeline__dot {
  position: absolute;
  left: -1.55rem;
  top: 0.3rem;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-accent);
  border: 2px solid var(--color-bg);
  box-shadow: 0 0 0 2px var(--color-accent);
}
.timeline__date {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-weight: 600;
}
.timeline__content h5 { margin: 0.25rem 0 0; font-size: 1rem; }
.timeline__content p { margin: 0.25rem 0 0; color: var(--color-text-secondary); }
```

---

## 11. chain

**用途**：递进链条。支持证据链和因果链两种模式。

**触发条件**：
- 列表或段落呈现"来源 → 引用 → 推理 → 结论"
- 列表项含递进/因果词，标题含"闭环/链条/流程"

**变体**：
- `chain--evidence`：来源 → 引用 → 推理 → 结论
- `chain--process`：简单箭头文本链

**变体选择规则**：
- 含明确"来源/引用/推理/结论" → `evidence`
- 否则 → `process`

```html
<ol class="chain chain--process">
  <li>八旗腐化是物质根基的动摇</li>
  <li>正统性必须靠叙事来弥补</li>
  <li class="chain__highlight">叙事又产生新的裂缝……</li>
</ol>
```

```css
.chain {
  list-style: none;
  padding: 0;
  margin: 1.5rem 0;
}
.chain li {
  position: relative;
  padding-left: 2rem;
  margin-bottom: 0.75rem;
  font-size: 1.05rem;
}
.chain li::before {
  content: "→";
  position: absolute;
  left: 0;
  color: var(--color-accent);
  font-weight: 700;
}
.chain__highlight {
  color: var(--color-accent);
  font-size: 1.2rem;
  font-weight: 700;
}

.chain--evidence {
  border-left: 3px solid var(--color-primary);
  padding-left: 1.5rem;
}
.chain--evidence li {
  padding: 0.75rem;
  margin-bottom: 0.75rem;
  background: var(--color-bg-soft);
  border-radius: var(--radius);
}
.chain--evidence li::before { display: none; }
.chain--evidence .chain__label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}
```

---

## 12. gap-box

**用途**：标注缺口、盲区、待验证假设。

**触发条件**：内容中出现"待补、缺口、盲区、未验证、假设、局限性"。

```html
<div class="gap-box">
  <div class="gap-box__label">待补</div>
  <p>缺口描述</p>
</div>
```

```css
.gap-box {
  background: var(--color-bg-muted);
  border: 2px dashed var(--color-text-muted);
  border-radius: var(--radius);
  padding: 1rem;
  margin: 1rem 0;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}
.gap-box__label {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  background: var(--color-border);
  padding: 0.1rem 0.5rem;
  border-radius: 3px;
  margin-bottom: 0.5rem;
}
```

---

## 13. badge-confidence

**用途**：标注结论置信度。

**触发条件**：结论段落中的置信度暗示词。默认不自动推断，仅当 agent 显式传入 `enable_confidence_badge=true` 或 Markdown 已含置信度标记时渲染。

```html
<span class="badge-confidence" data-level="H">H</span>
```

```css
.badge-confidence {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2em;
  height: 2em;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  color: #fff;
  vertical-align: middle;
  line-height: 1;
  font-family: "Noto Sans SC", sans-serif;
}
.badge-confidence[data-level="H"] { background: var(--color-success); }
.badge-confidence[data-level="M"] { background: var(--color-warning); color: var(--color-text); }
.badge-confidence[data-level="L"] { background: var(--color-danger); }
@media print {
  .badge-confidence[data-level="H"]::after { content: " ●"; color: var(--color-success); }
  .badge-confidence[data-level="M"]::after { content: " ●"; color: var(--color-warning); }
  .badge-confidence[data-level="L"]::after { content: " ●"; color: var(--color-danger); }
}
```

---

## 14. step-card

**用途**：步骤卡。序号 + 标题 + 内容 + 检查清单。

**触发条件**：
- 有序列表，项为"1. 2. 3."的连续步骤
- 包含"检查清单"、"TODO"、"第一步/第二步"等结构
- 标题含"步骤"、"流程"、"操作"

**数据提取**：
- steps：每个列表项提取 {title, content, checklist}
- title：步骤标题（加粗或首句）
- content：步骤描述
- checklist：子列表中的检查项（如有）

**HTML 模板**：

```html
<div class="step-card">
  <div class="step-card__number">1</div>
  <div class="step-card__body">
    <h5 class="step-card__title">步骤标题</h5>
    <p class="step-card__content">步骤详细描述</p>
    <div class="step-card__checklist">
      <div class="step-card__check-item">
        <input type="checkbox" id="step1-c1" />
        <label for="step1-c1">检查项1</label>
      </div>
    </div>
  </div>
</div>
```

```css
.step-card {
  display: flex;
  gap: 1rem;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 1.25rem;
  margin-bottom: 1rem;
  break-inside: avoid;
}
.step-card__number {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  font-weight: 800;
}
.step-card__body { flex: 1; }
.step-card__title {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  color: var(--color-text);
}
.step-card__content {
  margin: 0 0 0.75rem;
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}
.step-card__checklist {
  background: var(--color-bg-soft);
  border-radius: var(--radius);
  padding: 0.5rem 0.75rem;
}
.step-card__check-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.step-card__check-item input[type="checkbox"] {
  accent-color: var(--color-primary);
  width: 1rem;
  height: 1rem;
}
@media print {
  .step-card__check-item input[type="checkbox"] {
    appearance: none;
    border: 1px solid var(--color-text-muted);
    width: 0.8rem;
    height: 0.8rem;
    border-radius: 2px;
  }
}
```

---

## 15. toc-nav

**用途**：可选目录导航。sticky 侧边或浮动按钮。

**触发条件**：
- 报告正文较长（>2000字）
- 有 3+ 个一级标题
- 自动从标题结构生成

**数据提取**：
- items：从所有 `## ` / `### ` 标题提取 {text, anchor, level}
- 自动生成锚点（标题文本的 URL 安全版本）

**HTML 模板**：

```html
<nav class="toc-nav" id="toc-nav">
  <div class="toc-nav__toggle" id="toc-toggle" onclick="document.getElementById('toc-nav').classList.toggle('toc-nav--open')">
    目录
  </div>
  <ol class="toc-nav__list">
    <li class="toc-nav__item"><a href="#section-1">1. 章节1</a></li>
    <li class="toc-nav__item"><a href="#section-2">2. 章节2</a></li>
    <li class="toc-nav__item toc-nav__item--sub"><a href="#section-2-1">2.1 子章节</a></li>
  </ol>
</nav>
```

```css
.toc-nav {
  position: fixed;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  z-index: 100;
  font-size: 0.85rem;
}
.toc-nav__toggle {
  display: none;
  cursor: pointer;
  background: var(--color-primary);
  color: #fff;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius) 0 0 var(--radius);
  font-size: 0.8rem;
  font-weight: 600;
}
.toc-nav__list {
  list-style: none;
  margin: 0;
  padding: 0.75rem 1rem;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-right: none;
  border-radius: var(--radius) 0 0 var(--radius);
  box-shadow: var(--shadow-md);
  max-height: 70vh;
  overflow-y: auto;
}
.toc-nav__item { margin-bottom: 0.35rem; }
.toc-nav__item a {
  color: var(--color-text-secondary);
  text-decoration: none;
  display: block;
  padding: 0.15rem 0;
}
.toc-nav__item a:hover {
  color: var(--color-primary);
  text-decoration: underline;
}
.toc-nav__item--sub { padding-left: 1rem; font-size: 0.8rem; }

@media (max-width: 1024px) {
  .toc-nav__toggle { display: block; }
  .toc-nav__list { display: none; }
  .toc-nav--open .toc-nav__list { display: block; }
  .toc-nav--open .toc-nav__toggle { display: none; }
}
@media (max-width: 640px) {
  .toc-nav {
    top: auto;
    bottom: 1rem;
    right: 1rem;
    transform: none;
  }
  .toc-nav__toggle { border-radius: var(--radius); }
  .toc-nav__list {
    border-radius: var(--radius);
    border-right: 1px solid var(--color-border);
    max-height: 50vh;
    width: 60vw;
    max-width: 280px;
  }
}
@media print {
  .toc-nav { display: none; }
}
```

---

## 16. diagram

**用途**：流程图/架构图。节点 + 连线 + 自动布局。

**触发条件**：Markdown 中描述流程、架构、管线、决策树等拓扑结构的内容。

**HTML 模板**：

```html
<div class="diagram">
  <svg class="diagram__svg" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- 连线 -->
    <line/>
    <!-- 节点 -->
    <g class="diagram__node">
      <rect/>
      <text/>
    </g>
  </svg>
  <div class="diagram__caption">{caption}</div>
</div>
```

**生成逻辑**：
skill 根据 nodes 和 edges 数据自动计算布局：
1. 水平布局：节点从左到右排列，每节点宽 120px、高 50px、间距 40px
2. 垂直布局：节点从上到下排列
3. 连线用 `<line>` 或 `<path>`，带箭头 marker
4. 节点颜色映射到色板变量

```css
.diagram {
  margin: 1rem 0;
  break-inside: avoid;
}
.diagram__svg {
  width: 100%;
  height: auto;
  background: var(--color-bg-soft);
  border-radius: var(--radius);
}
.diagram__node rect {
  fill: var(--color-primary);
  rx: var(--radius);
}
.diagram__node text {
  fill: #fff;
  font-size: 12px;
  font-family: "IBM Plex Sans", sans-serif;
  text-anchor: middle;
  dominant-baseline: middle;
}
.diagram line, .diagram path {
  stroke: var(--color-text-muted);
  stroke-width: 2;
}
.diagram__caption {
  text-align: center;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-top: 0.5rem;
}
```

---

## 17. chart

**用途**：数据图表。柱状/折线/饼图。

**触发条件**：Markdown 中的数值数据列表或表格，可被可视化。

**HTML 模板**：

```html
<div class="chart">
  <svg class="chart__svg" viewBox="0 0 500 {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- 坐标轴、网格、数据图形 -->
  </svg>
  <div class="chart__caption">{title}</div>
</div>
```

**生成逻辑**：
skill 根据 type 和数据生成 SVG：
- **bar**：等宽柱状，自动计算 Y 轴刻度，柱宽 = 总宽/(n*1.5)
- **line**：折线+点，自动计算 Y 轴刻度，填充区域可选
- **pie**：饼图/环形图，自动计算角度，图例在右侧
- 颜色自动从色板分配（primary, accent, success, warning, danger, info...）

```css
.chart {
  margin: 1rem 0;
  break-inside: avoid;
}
.chart__svg {
  width: 100%;
  height: auto;
}
.chart__caption {
  text-align: center;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-top: 0.5rem;
}
```
