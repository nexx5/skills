# skills

Agent Skills 合集，发布由本人 [nexx5](https://github.com/nexx5) 创作或改编的 skill。

每个 skill 位于 `skills/<name>/`，可直接复制到 `~/.config/opencode/skills/` 或项目 `.opencode/skills/` 使用。

## 原创类

| Skill | 说明 |
|---|---|
| [多源搜索](skills/多源搜索/) | 统一多引擎搜索编排。支持 Bing/Baidu/SearXNG/Tavily 通用引擎 + arXiv/OpenAlex/Semantic Scholar 学术引擎并行搜索，及 webfetch/web-fetch.cmd/CloakBrowser/CDP 四级正文提取，结果合并打来源标签。 |
| [人类表达](skills/人类表达/) | 框架级去AI味方案（V3）。从AI与人表达的根本不同入手，生成侧管结构、判断侧管风格，统一判据"有托/无托"。叙事、评论、科普、口语、正式文案全场景适用，也用于润色改写提升质感。 |
| [去AI味儿](skills/去AI味儿/) | 写作硬约束层，用于已指定文风的场景，只负责"不要像AI"，不干预风格方向。注意：AI味儿并不是某些人以为的套路、范式固化，而是用词太"紧"——为效率过度优化、牺牲人性。本 skill 不采用"禁用词黑名单/固定句式模板"式机械过滤，而是采用"警惕而非禁止 + 场景诊断 + 逐句自检"：不定义文风，只确保输出在真实场景下像人说的。 |
| [快速调研师](skills/快速调研师/) | 通用深度调研分析师。融合多视角提问、agentic 检索闭环、强制引用与多源搜索，产出带来源标注的调研卷宗。适用"快速摸底话题/产品/技术/公司"、查证争议问题、竞品与替代方案调研。 |
| [逻辑陷阱](skills/逻辑陷阱/) | 逻辑谬误识别与反击。基于 7 大类 49 种逻辑陷阱模型，精准定性谈话/文章中的逻辑谬误，指出病灶并给出直接反击话术。 |
| [redfox](skills/redfox/) | 基于 RedFoxHub API 搜索小红书和公众号内容。两级搜索策略：先查优质库，结果不足时自动降级到广域库（仅公众号）。需自行配置 `REDFOX_API_KEY`（环境变量或 config.json）。 |
| [kb-retriever](skills/kb-retriever/) | 渐进式本地知识库检索。grep-first + 窗口读取，从不整文件加载，大语料下控制 token 消耗。支持文本与 PDF 检索。 |
| [subagent-resume](skills/subagent-resume/) | 接续中断的 sub agent，避免从头重派浪费。按任务名称查询 opencode 数据库匹配 sub agent session，返回 task_id + 中断状态，供 Task 工具恢复接续。**仅适用于 opencode 环境**。 |
| [MOA](skills/MOA/) | 跨会话多模型协作。plugin 负责传话，双方会话注册同一监听目录后自动配对启动，按角色（方案/审核、分析/评论等任意）迭代碰撞，输出含共识项/已采纳修订/分歧的三段文件。部署用随附 `scripts/deploy.js`。 |
| [MOA-Bot](skills/MOA-Bot/) | 基于现有会话的多 agent 协作。将任意正在运行的 opencode 会话注册为对等角色（方案A/方案B、答辩/审核等），内容经 `moa_bot_submit` 显式提交后注入对方会话，双方在各自上下文（记忆/工作目录/历史）中交互；plugin 自动配对、识别会话 ID、解读用户自然语言仲裁。无文件轮询、无手动转发、无持久化任务（关闭即结束）。与 MOA 的区别：不依赖共享监听目录，直接在会话间传话。 |
| [zhishibao](skills/zhishibao/) | 项目级结构化知识库。存储带边界/来源/置信度的知识"断言"，支持向量+关键词(FTS5)+关系三层检索，自动生成知识地图（L0-L2 视图）。数据与代码分离，每个项目一个知识包，可与深度调研 agent 集成。 |

## 改编/转载类

| Skill | 说明 |
|---|---|
| [html-report](skills/html-report/) | 智能 HTML 报告渲染引擎。research/editorial 双模式，输入自然 Markdown 自动做结构增强、语义分块、组件匹配，输出单文件自包含 HTML。适合调研报告、趋势解读、知识长文、公众号长图文。 |
| [qmd](skills/qmd/) | 本地文档搜索引擎（来自 [@tobilu/qmd](https://www.npmjs.com/package/@tobilu/qmd)）。BM25 全文搜索 + 向量语义搜索 + LLM 重排序，所有模型本地运行。 |
| [super-slide](skills/super-slide/) | 全景信息型幻灯片设计师。高密度、高级感，演讲/阅读双态兼顾。将文本重构为专业级视觉化的 HTML 幻灯片，支持外挂模板包切换视觉风格。 |
| [opendataloader-pdf](skills/opendataloader-pdf/) | PDF 数据提取工具（来自 [OpenDataLoader](https://github.com/opendataloader/opendataloader-pdf)）。基准测试第一的 PDF 解析器，支持本地模式与混合 AI 模式（复杂表格、扫描件、公式），输出 Markdown/JSON（带边界框）/HTML。 |

## 使用

```bash
cp -r skills/<name> ~/.config/opencode/skills/
```

## 许可

[Apache-2.0](LICENSE)
