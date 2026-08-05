# 数据可视化规则

## 编码方式

| 数据类型 | 推荐编码 | 说明 |
|---------|---------|------|
| 比例/占比 | 百分比水平条 | 长度编码，颜色区分类别 |
| 排名/排序 | 垂直条 | 高度编码，强调色标排名 |
| 流程/管道 | 水平箭头+节点色块 | 色块编码节点类型，线宽编码流量 |
| 对比/对照 | 左右分栏 | 50/50 或 60/40，用不同背景色 |
| 时间序列 | 迷你折线 | 小空间内展示趋势 |

## 条形图标准

```css
.bar-track {
  height: 10pt;
  background: var(--bgAlt);
  border-radius: 4pt;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4pt;
  transition: width 0.6s ease;
}
```

- 条高：9-10pt（配合正文）
- 圆角：4pt
- 颜色：仅使用模板包的 chartColors
- 可堆叠：用 flex 排列多条

## 过程节点标准

```css
.pipe-node {
  flex: 1;
  padding: 6pt 4pt;
  border-radius: 4pt;
  text-align: center;
  font-size: 8pt;
  font-weight: 600;
  color: #FFFFFF;
}
```

- 节点色：按模板包色彩编码
- 箭头：→ 字符或 SVG marker
- 间距：2-4pt 之间

## 表格标准

```css
table { width: 100%; border-collapse: collapse; font-size: 8pt; }
th { background: var(--primary); color: var(--textOnPrimary); padding: 4pt 6pt; }
td { padding: 3pt 6pt; border-bottom: 1px solid var(--border); }
tr:nth-child(even) td { background: var(--bgAlt); }
```

- 行高压缩至 12-14pt（正文字号+上下padding）
- 交替行色提高可读性
- 首列用 bold + primary color
