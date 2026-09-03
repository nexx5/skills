# 色板 + 排版参数 + 间距Token

> 所有CSS变量与 `components.md` 中的组件CSS保持一致命名。

## 色板A：blue-orange（技术/调研，默认）

```css
:root[data-theme="blue-orange"] {
  /* 主色 */
  --color-primary: #003f5c;
  --color-primary-light: #4da6c9;
  --color-primary-dark: #002a3d;
  --color-accent: #ff7c43;
  --color-accent-light: #ffa600;
  /* 语义色 */
  --color-success: #2ca02c;
  --color-warning: #ff7c43;
  --color-danger: #d62728;
  --color-info: #5b9bd5;
  /* 文字 */
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #94a3b8;
  /* 背景 */
  --color-bg: #ffffff;
  --color-bg-soft: #f8fafc;
  --color-bg-muted: #f1f5f9;
  /* 边框 */
  --color-border: #e2e8f0;
  /* 形状 */
  --radius: 6px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.1);
}
```

## 色板B：purple-green（商业/决策）

```css
:root[data-theme="purple-green"] {
  --color-primary: #3f007d;
  --color-primary-light: #9b6dd7;
  --color-primary-dark: #2a0054;
  --color-accent: #2ca02c;
  --color-accent-light: #98df8a;
  --color-success: #2ca02c;
  --color-warning: #ffbb78;
  --color-danger: #d62728;
  --color-info: #7b2d8e;
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #94a3b8;
  --color-bg: #fafafa;
  --color-bg-soft: #f5f5f5;
  --color-bg-muted: #f0f0f0;
  --color-border: #ddd0dd;
  --radius: 6px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.1);
}
```

## 色板C：warm-paper（文史/知识创作）

```css
:root[data-theme="warm-paper"] {
  --color-primary: #1B365D;
  --color-primary-light: #5a8ab5;
  --color-primary-dark: #0f1f36;
  --color-accent: #c0392b;
  --color-accent-light: #e74c3c;
  --color-success: #2ca02c;
  --color-warning: #c0392b;
  --color-danger: #e74c3c;
  --color-info: #2c4a6e;
  --color-text: #1c1810;
  --color-text-secondary: #5a5040;
  --color-text-muted: #8b7355;
  --color-bg: #faf6f0;
  --color-bg-soft: #f5efe5;
  --color-bg-muted: #efe8db;
  --color-border: #d4c8b0;
  --radius: 6px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.1);
}
```

## 色板D：vintage-tech（复古技术海报）

```css
:root[data-theme="vintage-tech"] {
  /* 主色 */
  --color-primary: #722F37;
  --color-primary-light: #a34a52;
  --color-primary-dark: #4a1f24;
  --color-accent: #C5A55A;
  --color-accent-light: #d4bc7a;
  /* 语义色 */
  --color-success: #2ca02c;
  --color-warning: #C5A55A;
  --color-danger: #d62728;
  --color-info: #5b9bd5;
  /* 文字 */
  --color-text: #333333;
  --color-text-secondary: #555555;
  --color-text-muted: #777777;
  /* 背景 */
  --color-bg: #F5F5DC;
  --color-bg-soft: #EFE8D0;
  --color-bg-muted: #E8DFC8;
  /* 边框 */
  --color-border: #8B4513;
  /* 形状 */
  --radius: 4px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.08);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.12);
  /* 复古纹理背景（可选） */
  --bg-texture: url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.08'/%3E%3C/svg%3E");
  /* 传统边框样式 */
  --border-style: double;
  --border-width: 3px;
}
```

## 色板E：poster-vintage（复古海报）

基于复古技术海报风格，米黄底色 + 深红主色 + 双线边框 + 衬线字体。

```css
:root[data-theme="poster-vintage"] {
  /* 主色 — 深红褐，用于标题条/数字/强调 */
  --color-primary: #7A1A1A;
  --color-primary-light: #A04040;
  --color-primary-dark: #5A1010;
  /* 强调色 — 暗金，用于装饰线/次要强调 */
  --color-accent: #8B6914;
  --color-accent-light: #B8941F;
  /* 语义色 */
  --color-success: #2E6B2E;
  --color-warning: #8B6914;
  --color-danger: #7A1A1A;
  --color-info: #4A5A6A;
  /* 文字 */
  --color-text: #2C1810;
  --color-text-secondary: #5C4030;
  --color-text-muted: #8B7355;
  /* 背景 — 米黄牛皮纸 */
  --color-bg: #F3E9D4;
  --color-bg-soft: #EDE0C8;
  --color-bg-muted: #E2D2B6;
  /* 边框 — 深棕 */
  --color-border: #5C3A20;
  /* 形状 */
  --radius: 3px;
  --shadow-sm: 0 1px 3px rgba(0,0,0,.1);
  --shadow-md: 0 2px 6px rgba(0,0,0,.15);
  /* 海报特有 */
  --border-style: double;
  --border-width: 3px;
  --border-double-gap: 2px;
  /* 点线引导颜色 */
  --color-leader: #A09080;
  /* 图标颜色 */
  --color-icon: #2C1810;
}
```

### poster-vintage 排版覆盖

```css
:root[data-theme="poster-vintage"] {
  font-size: 16px;
  line-height: 1.55;
}

[data-theme="poster-vintage"] body {
  font-family: 'Noto Serif SC', 'SimSun', 'STSong', 'Songti SC', Georgia, serif;
}

[data-theme="poster-vintage"] h1,
[data-theme="poster-vintage"] h2,
[data-theme="poster-vintage"] h3,
[data-theme="poster-vintage"] h4,
[data-theme="poster-vintage"] h5,
[data-theme="poster-vintage"] h6 {
  font-family: 'Noto Serif SC', 'SimSun', 'STSong', Georgia, 'Times New Roman', serif;
  font-weight: 900;
}

[data-theme="poster-vintage"] h1 {
  font-size: 2.8em;
  line-height: 1.15;
  letter-spacing: 0.02em;
  margin: 0.1em 0 0.15em;
}

[data-theme="poster-vintage"] h2 {
  font-size: 1.6em;
  line-height: 1.25;
  color: var(--color-primary);
  margin: 0.8em 0 0.4em;
}

[data-theme="poster-vintage"] h3 {
  font-size: 1.2em;
  color: var(--color-primary);
}
```

### poster-vintage 暗色变体

```css
html.dark[data-theme="poster-vintage"] {
  --color-primary: #C06060;
  --color-primary-light: #E09090;
  --color-primary-dark: #A04040;
  --color-accent: #B8941F;
  --color-accent-light: #D4B030;
  --color-success: #5A9A5A;
  --color-warning: #B8941F;
  --color-danger: #C06060;
  --color-info: #7AA0C0;
  --color-text: #E0D5C0;
  --color-text-secondary: #B0A090;
  --color-text-muted: #807060;
  --color-bg: #1E1810;
  --color-bg-soft: #2A2018;
  --color-bg-muted: #362C20;
  --color-border: #6A4A30;
  --color-leader: #6A5A4A;
  --color-icon: #D0C0A0;
}
```

## 暗色模式

每套色板配套暗色变体，通过 `html.dark` 激活：

```css
html.dark[data-theme="blue-orange"] {
  --color-primary: #4da6c9;
  --color-primary-light: #6bc4e6;
  --color-primary-dark: #3a8bb0;
  --color-accent: #ff9a5c;
  --color-accent-light: #ffc060;
  --color-success: #4ade80;
  --color-warning: #fbbf24;
  --color-danger: #f87171;
  --color-info: #7dd3fc;
  --color-text: #d4d4d4;
  --color-text-secondary: #a3a3a3;
  --color-text-muted: #737373;
  --color-bg: #1a1a2e;
  --color-bg-soft: #242440;
  --color-bg-muted: #2a2a4a;
  --color-border: #3a3a5c;
}

html.dark[data-theme="purple-green"] {
  --color-primary: #9b6dd7;
  --color-primary-light: #b88eea;
  --color-primary-dark: #7a50b8;
  --color-accent: #5fd65f;
  --color-accent-light: #a0f0a0;
  --color-success: #4ade80;
  --color-warning: #fbbf24;
  --color-danger: #f87171;
  --color-info: #c4a5e6;
  --color-text: #d4d4d4;
  --color-text-secondary: #a3a3a3;
  --color-text-muted: #737373;
  --color-bg: #1a1a28;
  --color-bg-soft: #242438;
  --color-bg-muted: #2a2a40;
  --color-border: #3a3a50;
}

html.dark[data-theme="warm-paper"] {
  --color-primary: #5a8ab5;
  --color-primary-light: #7aa8d4;
  --color-primary-dark: #4a7a9f;
  --color-accent: #e05a4a;
  --color-accent-light: #f07060;
  --color-success: #4ade80;
  --color-warning: #fbbf24;
  --color-danger: #f87171;
  --color-info: #8ab8e0;
  --color-text: #c8c0b0;
  --color-text-secondary: #a09888;
  --color-text-muted: #7a7060;
  --color-bg: #1c1810;
  --color-bg-soft: #2a2418;
  --color-bg-muted: #383020;
  --color-border: #4a4030;
}

html.dark[data-theme="vintage-tech"] {
  --color-primary: #a34a52;
  --color-primary-light: #c06a72;
  --color-primary-dark: #7a3038;
  --color-accent: #d4bc7a;
  --color-accent-light: #e0cc90;
  --color-success: #4ade80;
  --color-warning: #fbbf24;
  --color-danger: #f87171;
  --color-info: #7dd3fc;
  --color-text: #d4d0c0;
  --color-text-secondary: #a09888;
  --color-text-muted: #7a7060;
  --color-bg: #1a1810;
  --color-bg-soft: #242018;
  --color-bg-muted: #302820;
  --color-border: #5a4030;
}
```

### 暗色模式切换脚本

```html
<script>
  (function(){
    var d=document.documentElement,c=localStorage.getItem('theme-mode');
    if(c==='dark'||(!c&&window.matchMedia('(prefers-color-scheme:dark)').matches)){d.classList.add('dark')}
  })();
  function toggleDark(){
    var d=document.documentElement;
    d.classList.toggle('dark');
    localStorage.setItem('theme-mode',d.classList.contains('dark')?'dark':'light');
  }
</script>
```

按钮：
```html
<button onclick="toggleDark()" style="position:fixed;top:1rem;right:1rem;z-index:999;border:1px solid var(--color-border);background:var(--color-bg-soft);color:var(--color-text);padding:6px 10px;border-radius:var(--radius);cursor:pointer;font-size:0.85em;">暗色</button>
```

## 排版参数

```css
:root {
  font-size: 17px;
  line-height: 1.6;
  max-width: 42em;
  orphans: 3;
  widows: 3;
}

body {
  font-family: Charter, Georgia, 'Noto Serif SC', serif;
  color: var(--color-text);
  background: var(--color-bg);
}

h1, h2, h3, h4, h5, h6 {
  font-family: "IBM Plex Sans", 'Noto Sans SC', sans-serif;
  font-weight: bold;
}

h1 { font-size: 1.5em; }
h2 { font-size: 1.25em; }
h3 { font-size: 1.1em; }

blockquote, figure, table {
  page-break-inside: avoid;
}

h1, h2, h3 {
  page-break-after: avoid;
}
```

## 间距Token

```css
:root {
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
}
```

## 基础布局CSS

### 单栏居中（默认）

```css
.report-body {
  max-width: 42em;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
}
```

### Tufte边栏布局（可选）

```css
.report-body.tufte {
  max-width: 56em;
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
}

.report-body.tufte main {
  max-width: 36em;
}

.report-body.tufte aside.sidenote,
.report-body.tufte .margin-note {
  float: right;
  clear: right;
  margin-right: -18em;
  width: 15em;
  font-size: 0.85em;
  line-height: 1.4;
  color: var(--color-text-muted);
  border-left: 1px solid var(--color-border);
  padding-left: var(--space-sm);
}

.report-body.tufte .full-width {
  margin-right: -18em;
  width: calc(100% + 18em);
}
```

### 海报布局（poster）

```css
/* 海报整体框架：通栏标题 + 主内容网格 */
.report-body.poster {
  max-width: 72em;
  margin: 0 auto;
  padding: var(--space-lg) var(--space-xl);
  display: grid;
  grid-template-columns: 1fr 18em;
  grid-template-rows: auto 1fr;
  gap: var(--space-md);
}

/* 通栏标题区 — 横跨两栏 */
.poster-header {
  grid-column: 1 / -1;
  text-align: center;
  padding-bottom: var(--space-md);
  border-bottom: var(--border-width) var(--border-style) var(--color-border);
  margin-bottom: var(--space-sm);
}

.poster-header h1 {
  margin: 0;
  font-size: 2.8em;
  line-height: 1.15;
  color: var(--color-text);
}

.poster-header .poster-subtitle {
  font-size: 1.3em;
  color: var(--color-primary);
  margin-top: 0.2em;
  font-weight: 700;
}

.poster-header .poster-lead {
  font-size: 0.95em;
  color: var(--color-text-secondary);
  margin-top: 0.5em;
  line-height: 1.5;
  max-width: 48em;
  margin-left: auto;
  margin-right: auto;
}

/* 主内容区 */
.poster-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

/* 侧栏 */
.poster-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

/* 响应式 */
@media (max-width: 860px) {
  .report-body.poster {
    grid-template-columns: 1fr;
  }
  .poster-sidebar {
    order: -1;
    flex-direction: row;
    flex-wrap: wrap;
  }
  .poster-sidebar > * {
    flex: 1 1 45%;
  }
}

@media (max-width: 520px) {
  .report-body.poster {
    padding: var(--space-md) var(--space-sm);
  }
  .poster-header h1 {
    font-size: 1.8em;
  }
  .poster-sidebar {
    flex-direction: column;
  }
  .poster-sidebar > * {
    flex: 1 1 100%;
  }
}
```
