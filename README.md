# skills

Agent Skills 合集，发布由本人 [nexx5](https://github.com/nexx5) 创作或改编的skill。

每个 skill 位于 `skills/<name>/`，可直接复制到 `~/.config/opencode/skills/` 或项目 `.opencode/skills/` 使用。

## 原创类

| Skill | 说明 |
|---|---|
| [多源搜索](skills/多源搜索/) | 统一多引擎搜索编排。支持 Bing/Baidu/SearXNG/Tavily 通用引擎 + arXiv/OpenAlex/Semantic Scholar 学术引擎并行搜索，及 webfetch/web-fetch.cmd/CloakBrowser/CDP 四级正文提取，结果合并打来源标签。 |
| [html-report](skills/html-report/) | 智能 HTML 报告渲染引擎。research/editorial 双模式，输入自然 Markdown 自动做结构增强、语义分块、组件匹配，输出单文件自包含 HTML。适合调研报告、趋势解读、知识长文、公众号长图文。 |

## 改编/转载类


## 使用

```bash
cp -r skills/<name> ~/.config/opencode/skills/
```

## 许可

[Apache-2.0](LICENSE)
