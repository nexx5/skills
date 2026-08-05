---
name: redfox
description: 基于 RedFoxHub API 搜索小红书和公众号内容。适用于：(1) 搜索小红书图文/视频笔记，(2) 搜索公众号文章，(3) 搜索小红书/公众号账号。支持两级搜索策略：先查优质库，信息不足时自动降级到广域库（仅公众号）。需要 REDFOX_API_KEY。
---

# RedFox API Search

通过 RedFoxHub API 搜索小红书和公众号内容。

## 前置条件

在 `config.json` 中填入 `api_key`，或设置环境变量 `REDFOX_API_KEY`。

## 两级搜索策略

1. **先搜优质库**：调用 `--lib premium`（默认）。若结果数 ≥ 阈值（如 10 条）且满足需求，结束。
2. **不足则降级**：若优质库结果不足（太少或无相关结果），公众号可降级到 **广域库** `--lib broad`，返回的数据含 `content`（HTML 正文全文）。小红书只有优质库，无法降级。

## 使用方式

```bash
# 搜索小红书笔记（优质库）
python scripts/redfox_search.py xiaohongshu "<关键词>"

# 搜索公众号文章（优质库）
python scripts/redfox_search.py gongzhonghao "<关键词>"

# 搜索公众号文章（广域库，含正文）
python scripts/redfox_search.py gongzhonghao "<关键词>" --lib broad

# 分页/排序
python scripts/redfox_search.py xiaohongshu "<关键词>" --offset 20 --sort newest

# 输出原始 JSON
python scripts/redfox_search.py xiaohongshu "<关键词>" --raw
```

## 工作流

### 1. 判断用户意图

- "搜小红书上的 XX 内容" → 小红书搜索作品
- "搜公众号的 XX 文章" → 公众号搜索作品
- "找小红书/公众号的 XX 博主" → 搜索账号

### 2. 执行搜索

先用优质库搜索：

```bash
python scripts/redfox_search.py <平台> "<关键词>"
```

检查结果。若 `total` 为 0 或结果明显不够，且平台为 `gongzhonghao`，降级到广域库：

```bash
python scripts/redfox_search.py gongzhonghao "<关键词>" --lib broad
```

### 3. 呈现结果

对返回的每项结果，呈现标题、作者、互动数据（赞/阅读/收藏）、发布时间和链接。

若用户需要文章正文（仅公众号广域库），读取 `content` 字段的 HTML。

## 接口参考

各接口的详细参数和响应字段见：

- [小红书 API](references/xiaohongshu.md)
- [公众号 API](references/gongzhonghao.md)
