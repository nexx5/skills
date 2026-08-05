# 视觉补偿技法库

当内容密度不足以自然填满页面时，使用以下技法做视觉补偿。
每一页 slide 完成后，应检查是否有大块空白区域，如有则从中选择合适的技法填充。

## 技法速查

| 技法 | 代码实现 | 适用场景 | 使用建议 |
|------|---------|--------|---------|
| 区域底色区隔 | `.zone-bg { background: var(--bgAlt); }` | 任何场景 | 最优先的补偿手段 |
| 内边框装饰 | `border: 1px solid var(--border); border-radius: 6pt;` | 内容卡片 | 始终开启 |
| 四角角标 | `::before/::after` 画L形线 | 技术/专业内容 | 仅当页面有矩形区域时 |
| 网格底纹 | `background-image: linear-gradient(...)` | 科技/极简风 | 透明度<3% |
| 标签徽章 | `.badge { padding: 2pt 8pt; border-radius: 3pt; }` | 任何场景 | 用强调色 |
| 装饰性分隔线 | `.divider { background: linear-gradient(90deg, accent, transparent); }` | 段落之间 | 渐变收尾 |
| 首字下沉 | `::first-letter { font-size: 3em; float: left; }` | 文字段落 | 仅编辑风 |
| 基线参考线 | `background-size: 100% 12pt;` 画水平参考线 | 极简风 | 透明度<2% |
| 微型色标条 | `width: 3pt; border-left: 3pt solid accent;` | 卡片边缘 | 始终开启 |
| 编号水印 | 大号半透明数字作为背景装饰 | 列表内容 | 透明度<8% |

## 各模板推荐的补偿组合

| 模板 | 推荐的补偿技法 |
|------|--------------|
| consulting-navy | 区域底色区隔 + 内边框 + 色标条 + 角标 |
| tech-cyber | 网格底纹 + 色标条 + 角标 + 微光晕 |
| editorial-cream | 首字下沉 + 装饰性分隔线 + 色标条 |
| modern-minimal | 网格底纹 + 基线参考线 + 区域底色区隔 |

## CSS 参考

```css
/* 色标条 */
.card-accent {
  border-left: 3px solid var(--accent);
}

/* 四角角标 */
.zone::before,
.zone::after {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  border-color: var(--accent);
  border-style: solid;
  opacity: 0.3;
}

/* 渐变分隔线 */
.divider-accent {
  height: 1px;
  background: linear-gradient(90deg, var(--accent) 0%, transparent 100%);
  border: none;
}

/* 编号水印 */
.number-watermark {
  position: absolute;
  font-size: 48pt;
  font-weight: 900;
  color: var(--textMuted);
  opacity: 0.06;
  pointer-events: none;
}
```
