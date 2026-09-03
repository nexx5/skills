# 原子组件库

> 所有组件：零外部依赖 · CSS变量引用色板 · 响应式 · 打印友好
> agent无感知：agent不写任何标记，skill自动识别内容模式并渲染

---

## 1. badge-confidence

置信度徽章：🟢 H / 🟡 M / 🔴 L

**用途**：标注结论的置信度等级，可内联于任何卡片或段落。


**触发条件**：发现/结论段落中的置信度暗示词（"确定/证实/实验"→H，"可能/倾向"→M，"假设/推测/单源"→L）

**数据提取**：
- 从段落中提取置信度关键词，映射为H/M/L
- 自动推断：无明确证据支撑→L，多源印证→H

**HTML模板**：
```html
<span class="badge-confidence" data-level="H">H</span>
<span class="badge-confidence" data-level="M">M</span>
<span class="badge-confidence" data-level="L">L</span>
```

```css
.badge-confidence {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2em;
  height: 2em;
  border-radius: 50%;
  font-size: .75rem;
  font-weight: 700;
  color: #fff;
  vertical-align: middle;
  line-height: 1;
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

## 2. card-finding

发现卡片：结论 + 置信度 + 依据 + 缺口 四栏

**用途**：呈现单条调研发现，是报告最核心的组件。


**触发条件**：结论性段落（"结论是"、"我们发现"、"实验表明"开头），包含证据和可能的缺口

**数据提取**：
- title：段落标题或首句
- level：从措辞推断（"实验证实"→H，"可能"→M，"假设"→L）
- conclusion：核心结论句
- evidence：引用的来源、数据、实验结果
- gap："待验证"、"未测试"、"假设"等后续信息
- source：文末或括号中的来源标注

**HTML模板**：
```html
<div class="card-finding">
  <div class="card-finding__header">
    <h4 class="card-finding__title">结论标题</h4>
    <span class="badge-confidence" data-level="H">H</span>
  </div>
  <div class="card-finding__body">
    <div class="card-finding__conclusion">结论正文</div>
    <div class="card-finding__evidence">
      <strong>依据</strong>
      <ul>
        <li>依据1</li>
        <li>依据2</li>
      </ul>
    </div>
    <div class="card-finding__gap">
      <strong>缺口</strong>
      <p>待补充信息</p>
    </div>
  </div>
  <div class="card-finding__footer">
    <span class="source-tag">作者 · 标题</span>
  </div>
</div>
```

```css
.card-finding {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 1.25rem;
  margin-bottom: 1rem;
  break-inside: avoid;
}
.card-finding__header {
  display: flex;
  align-items: center;
  gap: .5rem;
  margin-bottom: .75rem;
}
.card-finding__title {
  margin: 0;
  font-size: 1rem;
  color: var(--color-text);
  flex: 1;
}
.card-finding__body {
  display: grid;
  grid-template-columns: 1fr;
  gap: .75rem;
  font-size: .9rem;
  color: var(--color-text-secondary);
}
@media (min-width: 640px) {
  .card-finding__body {
    grid-template-columns: 2fr 1fr;
  }
  .card-finding__gap { grid-column: 1 / -1; }
}
.card-finding__conclusion { line-height: 1.6; }
.card-finding__evidence ul { margin: .25rem 0; padding-left: 1.25rem; }
.card-finding__gap {
  background: var(--color-bg-muted);
  border: 1px dashed var(--color-text-muted);
  border-radius: var(--radius);
  padding: .5rem .75rem;
  font-size: .85rem;
  color: var(--color-text-muted);
}
.card-finding__footer {
  margin-top: .75rem;
  padding-top: .5rem;
  border-top: 1px solid var(--color-border);
}
```

---

## 3. card-comparison

对比卡片：A vs B 左右分栏

**用途**：两个方案/产品/观点的并排对比。


**触发条件**：
- 表格只有2-3列且表头暗示对比（"维度/A/B"、"特性/方案1/方案2"）
- 段落中出现"vs"、"对比"、"相比"等词
- 列表中有成对的"优势/短板"、"优点/缺点"

**数据提取**：
- title：对比主题（从标题或关键词提取）
- sides：从表格行或列表对中提取两侧内容
- verdict：末尾的总结性判定句

**HTML模板**：
```html
<div class="card-comparison">
  <div class="card-comparison__header">
    <h4 class="card-comparison__title">对比标题</h4>
  </div>
  <div class="card-comparison__grid">
    <div class="card-comparison__side" data-side="a">
      <h5>方案 A</h5>
      <ul>
        <li>特点1</li>
        <li>特点2</li>
      </ul>
    </div>
    <div class="card-comparison__divider"></div>
    <div class="card-comparison__side" data-side="b">
      <h5>方案 B</h5>
      <ul>
        <li>特点1</li>
        <li>特点2</li>
      </ul>
    </div>
  </div>
  <div class="card-comparison__verdict">
    <strong>判定：</strong>简述优劣
  </div>
</div>
```

```css
.card-comparison {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 1.25rem;
  margin-bottom: 1rem;
  break-inside: avoid;
}
.card-comparison__title {
  margin: 0 0 .75rem;
  font-size: 1rem;
  text-align: center;
}
.card-comparison__grid {
  display: grid;
  grid-template-columns: 1fr 2px 1fr;
  gap: 0;
}
.card-comparison__side {
  padding: .75rem;
  font-size: .9rem;
  color: var(--color-text-secondary);
}
.card-comparison__side h5 {
  margin: 0 0 .5rem;
  font-size: .9rem;
  color: var(--color-primary);
}
.card-comparison__side ul { margin: 0; padding-left: 1.25rem; }
.card-comparison__divider {
  background: var(--color-border);
  margin: .5rem 0;
}
.card-comparison__verdict {
  margin-top: .75rem;
  padding-top: .5rem;
  border-top: 1px solid var(--color-border);
  font-size: .9rem;
  color: var(--color-text-secondary);
  text-align: center;
}
@media (max-width: 480px) {
  .card-comparison__grid {
    grid-template-columns: 1fr;
  }
  .card-comparison__divider {
    height: 2px;
    margin: 0 .5rem;
  }
}
```

---

## 4. conflict-view

矛盾对撞：分栏 + 中间分歧焦点标注

**用途**：呈现两个来源/观点的矛盾，不裁决，只暴露分歧。


**触发条件**：
- 段落中出现"争议"、"矛盾"、"冲突"、"分歧"、"对立"等词
- 列表中有"立场A/立场B"、"支持/反对"成对结构
- 引用块中包含对立观点

**数据提取**：
- title：矛盾焦点（从"焦点是"、"争议在于"等提取）
- left/right：两个对立观点的内容和来源
- focus：核心分歧点
- status：裁决状态（"待补充"、"尚无定论"等）

**HTML模板**：
```html
<div class="conflict-view">
  <div class="conflict-view__header">
    <h4 class="conflict-view__title">矛盾焦点标题</h4>
  </div>
  <div class="conflict-view__grid">
    <div class="conflict-view__side" data-side="a">
      <span class="source-tag">来源A</span>
      <p>观点A描述</p>
    </div>
    <div class="conflict-view__focal">
      <div class="conflict-view__focal-label">分歧焦点</div>
      <div class="conflict-view__focal-text">焦点简述</div>
    </div>
    <div class="conflict-view__side" data-side="b">
      <span class="source-tag">来源B</span>
      <p>观点B描述</p>
    </div>
  </div>
  <div class="conflict-view__status">
    裁决：待补充 → 建议搜索 "xxx"
  </div>
</div>
```

```css
.conflict-view {
  background: var(--color-bg);
  border: 2px solid var(--color-warning);
  border-radius: var(--radius);
  padding: 1.25rem;
  margin-bottom: 1rem;
  break-inside: avoid;
}
.conflict-view__title {
  margin: 0 0 .75rem;
  font-size: 1rem;
  color: var(--color-text);
}
.conflict-view__grid {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: .75rem;
  align-items: start;
}
.conflict-view__side {
  padding: .75rem;
  background: var(--color-bg-soft);
  border-radius: var(--radius);
  font-size: .9rem;
  color: var(--color-text-secondary);
}
.conflict-view__side p { margin: .5rem 0 0; line-height: 1.6; }
.conflict-view__focal {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: .5rem;
  min-width: 80px;
}
.conflict-view__focal-label {
  font-size: .7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-warning);
  letter-spacing: .05em;
  margin-bottom: .25rem;
}
.conflict-view__focal-text {
  font-size: .8rem;
  color: var(--color-text);
  text-align: center;
  writing-mode: vertical-rl;
}
.conflict-view__status {
  margin-top: .75rem;
  padding-top: .5rem;
  border-top: 1px dashed var(--color-text-muted);
  font-size: .85rem;
  color: var(--color-text-muted);
  text-align: center;
}
@media (max-width: 480px) {
  .conflict-view__grid {
    grid-template-columns: 1fr;
  }
  .conflict-view__focal {
    flex-direction: row;
    min-width: unset;
  }
  .conflict-view__focal-text {
    writing-mode: horizontal-tb;
  }
}
```

---

## 5. timeline-item

时间线条目：日期 + 事件 + 描述，竖向排列

**用途**：纵向叙事中的里程碑/事件序列。


**触发条件**：
- 列表项以日期/年份/时间（"2024-01"、"2023年"、"Q1"）开头
- 连续3+个时间序列条目
- 标题含"历程"、"演变"、"发展"、"历史"

**数据提取**：
- events：每个列表项提取 {date, title, desc}
- date：开头的日期/时间表达式
- title：日期后的短语（通常是加粗或简短）
- desc：剩余描述文本

**HTML模板**：
```html
<div class="timeline">
  <div class="timeline-item">
    <div class="timeline-item__dot"></div>
    <div class="timeline-item__content">
      <div class="timeline-item__date">2024-01</div>
      <h5 class="timeline-item__event">事件名称</h5>
      <p class="timeline-item__desc">事件描述文本</p>
    </div>
  </div>
  <div class="timeline-item">
    <div class="timeline-item__dot"></div>
    <div class="timeline-item__content">
      <div class="timeline-item__date">2024-06</div>
      <h5 class="timeline-item__event">事件名称</h5>
      <p class="timeline-item__desc">事件描述文本</p>
    </div>
  </div>
</div>
```

```css
.timeline {
  position: relative;
  padding-left: 2rem;
  margin-bottom: 1rem;
}
.timeline::before {
  content: "";
  position: absolute;
  left: .55rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}
.timeline-item {
  position: relative;
  margin-bottom: 1.25rem;
  break-inside: avoid;
}
.timeline-item__dot {
  position: absolute;
  left: -2rem;
  top: .3rem;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-primary);
  border: 2px solid var(--color-bg);
  box-shadow: 0 0 0 2px var(--color-primary);
}
.timeline-item__date {
  font-size: .8rem;
  color: var(--color-text-muted);
  font-weight: 600;
  margin-bottom: .15rem;
}
.timeline-item__event {
  margin: 0;
  font-size: .95rem;
  color: var(--color-text);
}
.timeline-item__desc {
  margin: .25rem 0 0;
  font-size: .9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}
```

---

## 6. gap-box

缺口/盲区框：虚线边框 + 浅灰背景 + 标注"待补"

**用途**：标记单源结论、未验证假设、开放问题。


**触发条件**：
- 内容中出现"待补"、"缺口"、"盲区"、"未验证"、"假设"、"未来工作"、"局限性"
- 单源结论（只有一个来源支撑）
- 引用块中包含"待确认"类信息

**数据提取**：
- label："待补"、"盲区"等（从关键词提取）
- desc：缺口的具体描述
- action："建议搜索"、"需补充"等后续行动

**HTML模板**：
```html
<div class="gap-box">
  <div class="gap-box__label">待补</div>
  <p>缺口描述：单源结论/未验证假设/开放问题</p>
  <div class="gap-box__action">建议搜索："<em>关键词</em>"</div>
</div>
```

```css
.gap-box {
  background: var(--color-bg-muted);
  border: 2px dashed var(--color-text-muted);
  border-radius: var(--radius);
  padding: 1rem;
  margin-bottom: 1rem;
  font-size: .9rem;
  color: var(--color-text-secondary);
  break-inside: avoid;
}
.gap-box__label {
  display: inline-block;
  font-size: .7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-text-muted);
  background: var(--color-border);
  padding: .1rem .5rem;
  border-radius: 3px;
  margin-bottom: .5rem;
  letter-spacing: .05em;
}
.gap-box p { margin: .25rem 0; line-height: 1.6; }
.gap-box__action {
  margin-top: .5rem;
  font-size: .85rem;
  color: var(--color-text-muted);
}
.gap-box__action em { font-style: normal; color: var(--color-primary); }
```

---

## 7. kpi-card

KPI 数字卡：大数字 + 标签 + 可选 sparkline

**用途**：关键指标的高亮展示。


**触发条件**：
- 列表项主要是"数字+标签"格式（"87% 市场占有率"）
- 段落中突出显示的关键数字
- 表格中的汇总数据行

**数据提取**：
- value：数字（百分比、计数、金额等）
- label：数字对应的指标名称
- sparkline：如有趋势数据列表，生成迷你折线
- source：数据来源标注

**HTML模板**：
```html
<div class="kpi-card">
  <div class="kpi-card__value">87%</div>
  <div class="kpi-card__label">市场占有率</div>
  <div class="kpi-card__sparkline">
    <!-- 可选：简单 SVG sparkline -->
    <svg viewBox="0 0 100 24" preserveAspectRatio="none" width="100%" height="24">
      <polyline fill="none" stroke="var(--color-primary)" stroke-width="2"
        points="0,20 20,16 40,12 60,8 80,10 100,4" />
    </svg>
  </div>
  <span class="source-tag">来源</span>
</div>
```

```css
.kpi-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 1.25rem;
  text-align: center;
  margin-bottom: 1rem;
  break-inside: avoid;
}
.kpi-card__value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1.1;
}
.kpi-card__label {
  font-size: .85rem;
  color: var(--color-text-secondary);
  margin-top: .25rem;
}
.kpi-card__sparkline {
 margin-top: .5rem;
}
```

---

## 15. rank-list（排行列表 — 海报专用）

排行列表：图标 + 标签 + 点线引导 + 右对齐大数字

**用途**：海报中的排行榜/成绩列表，还原参考图风格。

**触发条件**（仅 poster 布局生效）：
- 表格有两列，第一列为名称，第二列为数值
- 列表项格式为"名称 ... 数值"或"名称：数值"
- 标题含"成绩"、"排名"、"榜单"、"评分"

**数据提取**：
- title：排行标题
- items：每项提取 {icon, label, value}
- icon：自动分配 SVG 图标（terminal, code, shield, tool, trophy, graduate, robot, book, chart, mountain 等，按索引循环）

**HTML模板**：
```html
<div class="poster-card">
  <div class="poster-card__header">排行标题</div>
  <div class="rank-list">
    <div class="rank-list__item">
      <span class="rank-list__icon">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 3h8v8H3zm10 0h8v8h-8zM3 13h8v8H3zm10 0h8v8h-8z"/></svg>
      </span>
      <span class="rank-list__label">Terminal Bench 2.1</span>
      <span class="rank-list__leaders"></span>
      <span class="rank-list__value">82.7</span>
    </div>
    <div class="rank-list__item">
      <span class="rank-list__icon">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6z"/></svg>
      </span>
      <span class="rank-list__label">NL2Repo</span>
      <span class="rank-list__leaders"></span>
      <span class="rank-list__value">54.2</span>
    </div>
  </div>
</div>
```

**图标 SVG 集**（按索引循环使用）：
```html
<!-- icon-0: terminal -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 14H4V6h16v12zM6 10l4 3-4 3v-2h-2v-2h2v-1zm6 4h6v-1.5h-6V12zm0-3h6V9.5h-6V9z"/></svg>
<!-- icon-1: code -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6z"/></svg>
<!-- icon-2: shield -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L3 7v5c0 5.5 3.8 10.7 9 12 5.2-1.3 9-6.5 9-12V7l-9-5zm0 2.2L19 8v4c0 4.4-3 8.6-7 9.8-4-1.2-7-5.4-7-9.8V8l7-3.8z"/></svg>
<!-- icon-3: tool -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/></svg>
<!-- icon-4: trophy -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M19 5h-2V3H7v2H5c-1.1 0-2 .9-2 2v1c0 2.5 1.9 4.5 4.3 4.9.5 1.7 1.8 3.1 3.5 3.7V19H7v2h10v-2h-3.8v-3.3c1.7-.6 3-2 3.5-3.7C19.1 12.5 21 10.5 21 8V7c0-1.1-.9-2-2-2zM7 8V7h2v4.1C6.4 10.6 5 9.1 5 8V7h2zm12 1c0 1.1-1.4 2.6-4 2.9V7h2V7h2z"/></svg>
<!-- icon-5: graduate -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3L1 9l11 6 9-4.9V17h2V9L12 3zm0 13.3l-2.9-1.6L12 21l2.9-2.3L12 16.3zM5 13.4V19l7 4 7-4v-5.6l-7 3.7-7-3.7z"/></svg>
<!-- icon-6: robot -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a2 2 0 012 2c0 .7-.4 1.4-1 1.7V7h3v2h-1v3h1v2h-1v5h1v2h-2v-1H9v1H7v-2h1v-5H7v-2h1v-3H7V7h3V5.7c-.6-.3-1-1-1-1.7a2 2 0 012-2zm-3 7H7v3h2V9zm6 0h-2v3h2V9zM7 15H5v5h2v-5zm10 0h-2v5h2v-5z"/></svg>
<!-- icon-7: book -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4zm12 16H6v-8l2.5 1.5L11 16v4h-2v-2h2v-2h2v2h2v-2h2v4z"/></svg>
<!-- icon-8: chart -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 3v18h18v-2H5V3H3zm12 14h-2v-6h2v6zm-4-2H9V7h2v8z"/></svg>
<!-- icon-9: mountain -->
<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 6l-3.75 5.5-2.25-3L3 19h2l4.5-6.5 2.75 4H21l-5-8-2 1.5z"/></svg>
```

```css
/* 排行列表 — 图标 + 标签 + 点线 + 数字 */
.rank-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: var(--space-sm) 0;
}

.rank-list__item {
  display: flex;
  align-items: baseline;
  padding: 0.45em 0;
  border-bottom: 1px dotted var(--color-leader);
  font-size: 1em;
}

.rank-list__item:last-child {
  border-bottom: none;
}

.rank-list__icon {
  flex-shrink: 0;
  width: 1.6em;
  height: 1.6em;
  color: var(--color-icon);
  margin-right: 0.6em;
}

.rank-list__icon svg {
  width: 100%;
  height: 100%;
}

.rank-list__label {
  flex-shrink: 0;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
}

.rank-list__leaders {
  flex: 1;
  border-bottom: 2px dotted var(--color-leader);
  margin: 0 0.5em;
  position: relative;
  top: -0.15em;
}

.rank-list__value {
  flex-shrink: 0;
  font-size: 1.5em;
  font-weight: 800;
  color: var(--color-primary);
  font-family: Georgia, 'Times New Roman', serif;
  line-height: 1;
}

@media (max-width: 520px) {
  .rank-list__value {
    font-size: 1.2em;
  }
  .rank-list__icon {
    width: 1.3em;
    height: 1.3em;
  }
}
```

---

## 16. poster-card（海报卡片 — 色块标题条）

海报卡片：深红标题条 + 双线边框 + 圆角 + 内容区

**用途**：海报中所有内容容器的统一卡片样式。

**触发条件**：poster 布局下自动包裹所有内容块。

**HTML模板**：
```html
<div class="poster-card">
  <div class="poster-card__header">卡片标题</div>
  <div class="poster-card__body">
    <!-- 内容：rank-list / 段落 / 列表 / 概念卡等 -->
  </div>
</div>
```

```css
.poster-card {
  background: var(--color-bg);
  border: var(--border-width) var(--border-style) var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  break-inside: avoid;
}

.poster-card__header {
  background: var(--color-primary);
  color: #FDF8F0;
  font-size: 1em;
  font-weight: 700;
  padding: 0.4em 0.9em;
  letter-spacing: 0.06em;
  display: inline-block;
}

.poster-card__body {
  padding: 0.6em 0.9em 0.9em;
}

/* 无标题的简化卡片 */
.poster-card[data-variant="plain"] .poster-card__body {
  padding-top: 0.9em;
}
```

---

## 17. poster-sidebar-item（侧栏内容块 — 海报专用）

侧栏内容块：紧凑卡片 + 标题 + 正文 + 装饰分隔

**用途**：海报右侧栏的独立内容块。

**触发条件**：poster 布局中，放在 `.poster-sidebar` 内的内容块。

**HTML模板**：
```html
<div class="poster-sidebar-item">
  <div class="poster-sidebar-item__header">社论 · 快评</div>
  <div class="poster-sidebar-item__image">
    <!-- 装饰区域：可放 SVG 插画或留白 -->
  </div>
  <div class="poster-sidebar-item__body">
    <h4 class="poster-sidebar-item__title">更新聚焦 Agent 能力</h4>
    <p>在多轮规划、工具调用和复杂任务执行上表现显著提升。</p>
  </div>
  <div class="poster-divider">
    <span class="poster-divider__star">★</span>
  </div>
</div>
```

```css
.poster-sidebar-item {
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
  break-inside: avoid;
}

.poster-sidebar-item__header {
  background: var(--color-primary);
  color: #FDF8F0;
  font-size: 0.85em;
  font-weight: 700;
  padding: 0.35em 0.7em;
  text-align: center;
  letter-spacing: 0.08em;
}

.poster-sidebar-item__image {
  width: 100%;
  aspect-ratio: 4/3;
  background: var(--color-bg-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.poster-sidebar-item__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.poster-sidebar-item__body {
  padding: 0.6em 0.7em 0.8em;
}

.poster-sidebar-item__title {
  margin: 0 0 0.4em;
  font-size: 1em;
  color: var(--color-primary);
  line-height: 1.3;
}

.poster-sidebar-item__body p {
  margin: 0;
  font-size: 0.85em;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
```

---

## 18. poster-divider（装饰分隔符 — 海报专用）

装饰分隔符：横线 + 星号，用于卡片内部区隔

**用途**：海报卡片内的装饰性分隔。

**HTML模板**：
```html
<div class="poster-divider">
  <span class="poster-divider__star">★</span>
</div>
```

```css
.poster-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5em;
  padding: 0.3em 0;
}

.poster-divider::before,
.poster-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-border);
  opacity: 0.5;
}

.poster-divider__star {
  font-size: 0.7em;
  color: var(--color-primary);
  line-height: 1;
}
```

---

## 19. poster-icon-row（图标行 — 海报专用）

图标行：左侧图标 + 右侧文本列表

**用途**：海报中带图标的文本说明块，如"接口与兼容"部分。

**触发条件**：poster 布局中，列表项前有明确的图标标识。

**HTML模板**：
```html
<div class="poster-card">
  <div class="poster-card__header">接口与兼容</div>
  <div class="poster-card__body">
    <div class="poster-icon-row">
      <span class="poster-icon-row__icon">
        <!-- 齿轮图标 -->
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a2 2 0 012 2c0 .7-.4 1.4-1 1.7V7h3v2h-1v3h1v2h-1v5h1v2h-2v-1H9v1H7v-2h1v-5H7v-2h1v-3H7V7h3V5.7c-.6-.3-1-1-1-1.7a2 2 0 012-2z"/></svg>
      </span>
      <div class="poster-icon-row__content">
        <ul>
          <li>正式版 V4-Flash 原生支持 Responses API 格式</li>
          <li>并针对性适配 Codex</li>
        </ul>
      </div>
    </div>
  </div>
</div>
```

```css
.poster-icon-row {
  display: flex;
  gap: 0.7em;
  align-items: flex-start;
  padding: 0.3em 0;
}

.poster-icon-row__icon {
  flex-shrink: 0;
  width: 2.4em;
  height: 2.4em;
  color: var(--color-icon);
}

.poster-icon-row__icon svg {
  width: 100%;
  height: 100%;
}

.poster-icon-row__content {
  flex: 1;
  font-size: 0.9em;
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.poster-icon-row__content ul {
  margin: 0;
  padding-left: 1.2em;
}

.poster-icon-row__content li {
  margin-bottom: 0.2em;
}
```

---

## 20. poster-alert（海报提示框 — 海报专用）

海报提示框：大图标 + 醒目文字，用于重要提示

**用途**：海报底部的重要提示/注意事项区域。

**触发条件**：poster 布局中，含"注意"、"重要"、"提示"等关键词的段落。

**HTML模板**：
```html
<div class="poster-alert">
  <div class="poster-card__header">重要提示</div>
  <div class="poster-card__body">
    <div class="poster-alert__icon">
      <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-2h2v2h-2zm0-4V7h2v6h-2z"/></svg>
    </div>
    <div class="poster-alert__content">
      <p>本次仅升级了 API 接口，不影响现有服务与体验。</p>
    </div>
  </div>
</div>
```

```css
.poster-alert {
  background: var(--color-bg);
  border: var(--border-width) var(--border-style) var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
  break-inside: avoid;
}

.poster-alert__icon {
  float: left;
  width: 2.8em;
  height: 2.8em;
  color: var(--color-primary);
  margin-right: 0.6em;
  margin-top: 0.1em;
}

.poster-alert__icon svg {
  width: 100%;
  height: 100%;
}

.poster-alert__content p {
  font-size: 0.95em;
  color: var(--color-primary);
  line-height: 1.55;
  font-weight: 600;
}

.poster-alert__content p::before {
  content: "★ ";
  color: var(--color-primary);
}

---

## 8. evidence-chain

证据链：来源 → 引用 → 推理 → 结论，竖向连接

**用途**：展示从原始来源到最终结论的推理路径。


**触发条件**：
- 列表或段落呈现"来源→引用→推理→结论"递进结构
- 明确标注了引文、出处、推导步骤
- 标题含"证据"、"推导"、"论证"

**数据提取**：
- steps：按顺序提取 {type, content, level}
- type：从关键词推断（"来源"→source，"引用"→cite，"推理"→reason，"结论"→conclusion）
- level：仅conclusion步骤提取置信度

**HTML模板**：
```html
<div class="evidence-chain">
  <div class="evidence-chain__step" data-step="source">
    <div class="evidence-chain__marker">来源</div>
    <div class="evidence-chain__content">
      <span class="source-tag">作者 · 标题</span>
    </div>
  </div>
  <div class="evidence-chain__step" data-step="cite">
    <div class="evidence-chain__marker">引用</div>
    <div class="evidence-chain__content">
      <blockquote>原文引用内容</blockquote>
    </div>
  </div>
  <div class="evidence-chain__step" data-step="reason">
    <div class="evidence-chain__marker">推理</div>
    <div class="evidence-chain__content">
      <p>推理过程描述</p>
    </div>
  </div>
  <div class="evidence-chain__step" data-step="conclusion">
    <div class="evidence-chain__marker">结论</div>
    <div class="evidence-chain__content">
      <p><strong>最终结论</strong> <span class="badge-confidence" data-level="H">H</span></p>
    </div>
  </div>
</div>
```

```css
.evidence-chain {
  border-left: 3px solid var(--color-primary);
  padding-left: 1.5rem;
  margin: 1rem 0;
  break-inside: avoid;
}
.evidence-chain__step {
  position: relative;
  margin-bottom: 1rem;
  padding: .5rem .75rem;
  background: var(--color-bg-soft);
  border-radius: var(--radius);
}
.evidence-chain__step::before {
  content: "";
  position: absolute;
  left: -1.75rem;
  top: .75rem;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-primary);
}
.evidence-chain__marker {
  font-size: .7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-primary);
  letter-spacing: .05em;
  margin-bottom: .25rem;
}
.evidence-chain__content {
  font-size: .9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}
.evidence-chain__content blockquote {
  margin: .25rem 0;
  padding: .25rem .5rem;
  border-left: 3px solid var(--color-accent);
  background: var(--color-bg-muted);
  font-style: italic;
}
.evidence-chain__step[data-step="conclusion"] {
  background: var(--color-primary-light);
  color: var(--color-text);
}
.evidence-chain__step[data-step="conclusion"] .evidence-chain__marker {
  color: var(--color-primary-dark);
}
```

---

## 9. source-tag

来源标签：作者 · 标题，链接到原始 URL

**用途**：来源标注，可内联或放于卡片底部。


**触发条件**：
- 括号或文末的引用标注（"作者·标题"）
- Markdown链接 `[标题](URL)` 形式的来源
- 独立成行的来源信息

**数据提取**：
- url：链接URL（如有）
- author：作者名（从"作者·标题"格式提取）
- title：标题（从"作者·标题"格式提取）

**HTML模板**：
```html
<a class="source-tag" href="https://example.com" target="_blank" rel="noopener">
  作者 · 标题
</a>
<!-- 或无链接 -->
<span class="source-tag">作者 · 标题</span>
```

```css
.source-tag {
  display: inline-block;
  font-size: .8rem;
  color: var(--color-text-muted);
  background: var(--color-bg-muted);
  padding: .15rem .5rem;
  border-radius: 3px;
  text-decoration: none;
  line-height: 1.4;
  vertical-align: middle;
}
a.source-tag:hover {
  background: var(--color-primary-light);
  color: var(--color-primary-dark);
  text-decoration: none;
}
a.source-tag::after {
  content: " ↗";
  font-size: .7em;
}
```

---

## 10. concept-card

概念讲解卡：痛点 → 是什么 → 怎么工作 三段式

**用途**：向非专业读者解释核心概念。


**触发条件**：
- 段落结构为三段式："它是什么"/"为什么要分"/"怎么用"或类似变体
- 出现"痛点"、"是什么"、"怎么工作"、"为什么"、"怎么用"等标志性短语
- 对单一术语进行系统性解释

**数据提取**：
- name：概念名称（从标题或首句提取）
- pain："痛点"/"解决什么"/"为什么需要"段落
- what："是什么"/"定义"/"本质"段落
- how："怎么工作"/"怎么用"/"机制"段落
- boundary："边界"/"局限"/"注意事项"段落（如有）

**HTML模板**：
```html
<div class="concept-card">
  <h4 class="concept-card__title">概念名称</h4>
  <div class="concept-card__section" data-section="pain">
    <div class="concept-card__label">痛点</div>
    <p>没有这个概念时遇到了什么问题</p>
  </div>
  <div class="concept-card__section" data-section="what">
    <div class="concept-card__label">是什么</div>
    <p>这个概念的本质定义（3-5 句大白话）</p>
  </div>
  <div class="concept-card__section" data-section="how">
    <div class="concept-card__label">怎么工作</div>
    <p>核心机制/运作方式</p>
  </div>
</div>
```

```css
.concept-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 1.25rem;
  margin-bottom: 1rem;
  break-inside: avoid;
}
.concept-card__title {
  margin: 0 0 .75rem;
  font-size: 1rem;
  color: var(--color-primary-dark);
}
.concept-card__section {
  margin-bottom: .75rem;
  padding: .5rem .75rem;
  border-radius: var(--radius);
  font-size: .9rem;
  line-height: 1.6;
  color: var(--color-text-secondary);
}
.concept-card__section[data-section="pain"] {
  background: #fef2f2;
  border-left: 3px solid var(--color-danger);
}
.concept-card__section[data-section="what"] {
  background: var(--color-bg-soft);
  border-left: 3px solid var(--color-primary);
}
.concept-card__section[data-section="how"] {
  background: #f0fdf4;
  border-left: 3px solid var(--color-success);
}
.concept-card__label {
  font-size: .7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--color-text-muted);
  margin-bottom: .25rem;
}
```

---

## 11. step-card

步骤卡：序号 + 标题 + 内容 + 检查清单

**用途**：行动指南中的分步操作指引。


**触发条件**：
- 有序列表，项为"1. 2. 3."的连续步骤
- 包含"检查清单"、"TODO"、"第一步/第二步"等结构
- 标题含"步骤"、"流程"、"操作"

**数据提取**：
- steps：每个列表项提取 {title, content, checklist}
- title：步骤标题（加粗或首句）
- content：步骤描述
- checklist：子列表中的检查项（如有）

**HTML模板**：
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
      <div class="step-card__check-item">
        <input type="checkbox" id="step1-c2" />
        <label for="step1-c2">检查项2</label>
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
  margin: 0 0 .5rem;
  font-size: 1rem;
  color: var(--color-text);
}
.step-card__content {
  margin: 0 0 .75rem;
  font-size: .9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}
.step-card__checklist {
  background: var(--color-bg-soft);
  border-radius: var(--radius);
  padding: .5rem .75rem;
}
.step-card__check-item {
  display: flex;
  align-items: center;
  gap: .5rem;
  padding: .25rem 0;
  font-size: .85rem;
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
    width: .8rem;
    height: .8rem;
    border-radius: 2px;
  }
}
```

---

## 12. toc-nav

可选目录导航：sticky 侧边或浮动按钮

**用途**：长报告的章节快速跳转。


**触发条件**：
- 报告正文较长（>2000字）
- 有3+个一级标题
- 自动从标题结构生成

**数据提取**：
- items：从所有 `## ` / `### ` 标题提取 {text, anchor, level}
- 自动生成锚点（标题文本的URL安全版本）

**HTML模板**：
```html
<nav class="toc-nav" id="toc-nav">
  <div class="toc-nav__toggle" id="toc-toggle" onclick="document.getElementById('toc-nav').classList.toggle('toc-nav--open')">
    目录
  </div>
  <ol class="toc-nav__list">
    <li class="toc-nav__item"><a href="#section-1">1. 章节1</a></li>
    <li class="toc-nav__item"><a href="#section-2">2. 章节2</a></li>
    <li class="toc-nav__item toc-nav__item--sub"><a href="#section-2-1">2.1 子章节</a></li>
    <li class="toc-nav__item"><a href="#section-3">3. 章节3</a></li>
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
  font-size: .85rem;
}
.toc-nav__toggle {
  display: none;
  cursor: pointer;
  background: var(--color-primary);
  color: #fff;
  padding: .5rem .75rem;
  border-radius: var(--radius) 0 0 var(--radius);
  font-size: .8rem;
  font-weight: 600;
}
.toc-nav__list {
  list-style: none;
  margin: 0;
  padding: .75rem 1rem;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-right: none;
  border-radius: var(--radius) 0 0 var(--radius);
  box-shadow: var(--shadow-md);
  max-height: 70vh;
  overflow-y: auto;
}
.toc-nav__item { margin-bottom: .35rem; }
.toc-nav__item a {
  color: var(--color-text-secondary);
  text-decoration: none;
  display: block;
  padding: .15rem 0;
}
.toc-nav__item a:hover {
  color: var(--color-primary);
  text-decoration: underline;
}
.toc-nav__item--sub { padding-left: 1rem; font-size: .8rem; }

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
  .toc-nav__toggle {
    border-radius: var(--radius);
  }
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

## 13. diagram

流程图/架构图：节点 + 连线 + 自动布局

**用途**：展示流程、架构、管线、决策树等拓扑结构。


**HTML模板**：
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
skill根据nodes和edges数据自动计算布局：
1. 水平布局：节点从左到右排列，每节点宽120px、高50px、间距40px
2. 垂直布局：节点从上到下排列
3. 连线用`<line>`或`<path>`，带箭头marker
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
  font-size: .85rem;
  color: var(--color-text-muted);
  margin-top: .5rem;
}
```

---

## 14. chart

数据图表：柱状/折线/饼图

**用途**：数据可视化，替代纯数字列表。


**HTML模板**：
```html
<div class="chart">
  <svg class="chart__svg" viewBox="0 0 500 {height}" xmlns="http://www.w3.org/2000/svg">
    <!-- 坐标轴、网格、数据图形 -->
  </svg>
  <div class="chart__caption">{title}</div>
</div>
```

**生成逻辑**：
skill根据type和数据生成SVG：
- **bar**：等宽柱状，自动计算Y轴刻度，柱宽=总宽/(n*1.5)
- **line**：折线+点，自动计算Y轴刻度，填充区域可选
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
  font-size: .85rem;
  color: var(--color-text-muted);
  margin-top: .5rem;
}
```
