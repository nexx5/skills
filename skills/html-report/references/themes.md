# 色板 + 排版参数 + 间距 Token

> 所有 CSS 变量与 `components.md` 中的组件 CSS 保持一致命名。
> 4 套色板：editorial-warm（编辑式暖纸媒，默认）/ blue-orange（技术调研）/ purple-green（商业决策）/ warm-paper（文史知识创作）

## 主题 A：editorial-warm（编辑式暖纸媒，默认）

```css
:root[data-theme="editorial-warm"] {
  /* 主色 */
  --color-primary: #1c1810;
  --color-primary-light: #4a4030;
  --color-primary-dark: #0f0c08;

  /* 强调色 */
  --color-accent: #b8563f;
  --color-accent-light: #c96e55;
  --color-accent-dark: #8f3f2c;

  /* 辅助色 */
  --color-secondary: #2f5e4e;
  --color-secondary-light: #4a7a68;
  --color-secondary-dark: #1f4034;

  /* 语义色 */
  --color-success: #2f5e4e;
  --color-warning: #b8563f;
  --color-danger: #a9442f;
  --color-info: #5a5040;

  /* 文字 */
  --color-text: #1c1810;
  --color-text-secondary: #6b655c;
  --color-text-muted: #8b8175;

  /* 背景 */
  --color-bg: #f7f4ef;
  --color-bg-soft: #f0ece6;
  --color-bg-muted: #e9e4da;

  /* 边框与装饰 */
  --color-border: #d4c8b0;
  --color-topbar: var(--color-accent);

  /* 形状 */
  --radius: 4px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.04);
  --shadow-md: 0 4px 8px -2px rgba(0,0,0,.08);
}
```

## 主题 B：blue-orange（技术/调研）

```css
:root[data-theme="blue-orange"] {
  --color-primary: #003f5c;
  --color-primary-light: #4da6c9;
  --color-primary-dark: #002a3d;
  --color-accent: #ff7c43;
  --color-accent-light: #ffa600;
  --color-secondary: #2ca02c;
  --color-secondary-light: #5fd65f;
  --color-secondary-dark: #1a7a1a;
  --color-success: #2ca02c;
  --color-warning: #ff7c43;
  --color-danger: #d62728;
  --color-info: #5b9bd5;
  --color-text: #0f172a;
  --color-text-secondary: #475569;
  --color-text-muted: #94a3b8;
  --color-bg: #ffffff;
  --color-bg-soft: #f8fafc;
  --color-bg-muted: #f1f5f9;
  --color-border: #e2e8f0;
  --color-topbar: var(--color-primary);
  --radius: 6px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.1);
}
```

## 主题 C：purple-green（商业/决策）

```css
:root[data-theme="purple-green"] {
  --color-primary: #3f007d;
  --color-primary-light: #9b6dd7;
  --color-primary-dark: #2a0054;
  --color-accent: #2ca02c;
  --color-accent-light: #98df8a;
  --color-secondary: #7b2d8e;
  --color-secondary-light: #a855c0;
  --color-secondary-dark: #5a1a6e;
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
  --color-topbar: var(--color-primary);
  --radius: 6px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.1);
}
```

## 主题 D：warm-paper（文史/知识创作）

```css
:root[data-theme="warm-paper"] {
  --color-primary: #1B365D;
  --color-primary-light: #5a8ab5;
  --color-primary-dark: #0f1f36;
  --color-accent: #c0392b;
  --color-accent-light: #e74c3c;
  --color-secondary: #2c4a6e;
  --color-secondary-light: #4a6e9e;
  --color-secondary-dark: #1a3050;
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
  --color-topbar: var(--color-accent);
  --radius: 6px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,.1);
}
```

## 暗色模式

### editorial-warm 暗色变体

```css
html.dark[data-theme="editorial-warm"] {
  --color-primary: #d4c8b0;
  --color-primary-light: #e9dcc8;
  --color-primary-dark: #b0a490;
  --color-accent: #d97a60;
  --color-accent-light: #e89880;
  --color-accent-dark: #b85a42;
  --color-secondary: #6aa88e;
  --color-secondary-light: #8fc4ae;
  --color-secondary-dark: #4a806a;
  --color-success: #6aa88e;
  --color-warning: #d97a60;
  --color-danger: #c96452;
  --color-info: #a09888;
  --color-text: #e9e4da;
  --color-text-secondary: #b8b0a0;
  --color-text-muted: #8b8375;
  --color-bg: #1c1810;
  --color-bg-soft: #2a2418;
  --color-bg-muted: #383020;
  --color-border: #4a4030;
  --color-topbar: var(--color-accent);
}
```

### blue-orange 暗色变体

```css
html.dark[data-theme="blue-orange"] {
  --color-primary: #4da6c9;
  --color-primary-light: #6bc4e6;
  --color-primary-dark: #3a8bb0;
  --color-accent: #ff9a5c;
  --color-accent-light: #ffc060;
  --color-secondary: #5fd65f;
  --color-secondary-light: #a0f0a0;
  --color-secondary-dark: #3a9a3a;
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
  --color-topbar: var(--color-primary);
}
```

### purple-green 暗色变体

```css
html.dark[data-theme="purple-green"] {
  --color-primary: #9b6dd7;
  --color-primary-light: #b88eea;
  --color-primary-dark: #7a50b8;
  --color-accent: #5fd65f;
  --color-accent-light: #a0f0a0;
  --color-secondary: #a855c0;
  --color-secondary-light: #c080e0;
  --color-secondary-dark: #8040a0;
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
  --color-topbar: var(--color-primary);
}
```

### warm-paper 暗色变体

```css
html.dark[data-theme="warm-paper"] {
  --color-primary: #5a8ab5;
  --color-primary-light: #7aa8d4;
  --color-primary-dark: #4a7a9f;
  --color-accent: #e05a4a;
  --color-accent-light: #f07060;
  --color-secondary: #4a6e9e;
  --color-secondary-light: #6a8ebe;
  --color-secondary-dark: #3a5a80;
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
  --color-topbar: var(--color-accent);
}
```

## 暗色切换脚本

```html
<script>
  (function(){
    var d=document.documentElement, c=localStorage.getItem('theme-mode');
    if(c==='dark' || (!c && window.matchMedia('(prefers-color-scheme:dark)').matches)){
      d.classList.add('dark');
    }
  })();
  function toggleDark(){
    var d=document.documentElement;
    d.classList.toggle('dark');
    localStorage.setItem('theme-mode', d.classList.contains('dark')?'dark':'light');
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
  line-height: 1.85;
  --max-width-body: 42em;
  --max-width-wide: 56em;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 24px;
  --space-xl: 32px;
  --space-2xl: 48px;
}

body {
  font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", "STSong", serif;
  color: var(--color-text);
  background: var(--color-bg);
}

h1, h2, h3, h4 {
  font-family: "Noto Serif SC", "Source Han Serif SC", "SimSun", "STSong", serif;
  font-weight: 700;
  line-height: 1.3;
}

.section-label,
.kpi .label,
.source-footer,
.badge-confidence {
  font-family: "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
}
```

## 基础布局

### 单栏居中（默认）

```css
.report-body {
  max-width: var(--max-width-body);
  margin: 0 auto;
  padding: var(--space-xl) var(--space-lg);
}

body::before {
  content: "";
  display: block;
  height: 4px;
  background: var(--color-topbar);
}
```

### Tufte 边栏布局（可选）

```css
.report-body.tufte {
  max-width: var(--max-width-wide);
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
