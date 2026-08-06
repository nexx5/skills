---
name: zhishibao
description: 知识包能力：结构化知识的存储、融合与检索。当需要建立项目级知识库、写入断言/知识点、检索已有知识、生成知识地图时使用。支持向量语义检索+关键词检索+关系跳转。适用场景：(1)AI 产出洞察/断言需要沉淀复用，(2)检索已有知识支撑决策/回答，(3)跨断言发现关联与冲突，(4)生成知识地图概览。每个项目一个知识包，数据与代码分离。
---

# zhishibao 知识包

项目级结构化知识库。存储"断言"（带边界、来源、置信度的知识单元），提供向量+关键词+关系三层检索。

## 前置条件

- **Python 3.10+**：脚本仅使用标准库（sqlite3/urllib/json/argparse），无需 pip install。FTS5 trigram tokenizer 需 SQLite 3.34+（Python 3.10+ 自带）
- **嵌入 API**：需要一个 OpenAI 兼容的 embeddings 端点（用于向量检索）。在 `config.json` 中配置 base_url/api_key/model。若无配置，脚本会读环境变量（EMBED_BASE_URL/EMBED_API_KEY/EMBED_MODEL 或 QMD_OPENAI_*）
- **无需 LLM 配置**：语义融合判断（duplicate/merge/extend/conflict）由调用方 AI 完成，skill 脚本不调 LLM
- **Windows 终端编码**：脚本输出 UTF-8，PowerShell 终端默认 GBK 会显示中文乱码。本地调试时运行 `chcp 65001` 切换 UTF-8 代码页。AI 解析 JSON 字节流不受影响

## 脚本位置

所有脚本在本 skill 目录的 `scripts/` 下。调用时用完整路径：

```
python "<skill目录>/scripts/<脚本名>.py" --project-path "<项目根>" [其他参数]
```

`<skill目录>` 是本 SKILL.md 所在目录。`--project-path` 指向知识包所属项目根目录，知识包数据在 `<项目根>/knowledge-pack/`。

### "使用 skill" 与 "绕过 skill" 正名（关键，必读）

> **通过 `python "<skill目录>/scripts/<脚本>.py" --project-path ...` 调用本 skill 的脚本，就是"使用 skill"，不是"绕过 skill"**。本 skill 不内嵌 LLM，所有语义判断（duplicate/merge/extend/conflict）由调用方 AI 完成，脚本只执行写入/索引/嵌入/检索动作（见核心原则第5条）。

**"绕过 skill"的真实定义**（这些才是禁止的）：
- 自己用 sqlite3 写 SQL 查询 SQLite，替代 `knowledge-search.py` 的检索接口
- 自己用 glob+grep+Read 遍历 claims.jsonl/relations.jsonl 等数据文件，替代 skill 的检索接口
- 自己手写 claims.jsonl 不走 `knowledge-ingest.py` 的校验链路

**skill 脚本 vs 平台脚本**（区分，避免混淆）：
- **skill 脚本**（本 skill 提供）：在 `<skill目录>/scripts/`，含 knowledge-search/knowledge-ingest/generate-knowledge-views/build-relations/embed-claims/knowledge-db-init/knowledge-purge-by-source，通过 `python "<skill目录>/scripts/<脚本>.py" --project-path ...` 调用
- **平台脚本**（平台级，非本 skill）：在 `.opencode/scripts/`，含 check-research-state/checkpoint/merge-batch/check-plan-review-quality/rebuild-knowledge-index 等，通过 `python .opencode/scripts/<脚本>.py ...` 调用
- 两者都是直接用 python 完整路径调用，**均无任何禁止**

## 数据结构

```
<项目根>/knowledge-pack/
├── claims.jsonl        # 断言真相源（每行一条断言 JSON）
├── relations.jsonl     # AI 手动建的 strong 关系真相源
├── config.json         # 嵌入模型配置
├── index/knowledge.db  # SQLite 影子索引（可从 jsonl 重建）
└── views/L0-知识概貌.md # 自动生成的知识概貌（L0视图）
```

### relations.jsonl schema

每行一条 JSON，字段如下：
- `claim_a` (必填): 关系起点断言 ID
- `claim_b` (必填): 关系终点断言 ID
- `relation_type` (必填): extends/coexist/opposing/alternative_to/complements/similar_to/depends_on/supersedes/upstream_of
- `strength` (必填): strong 或 medium
- `context` (可选): 关系说明
- `created` (可选): ISO 8601 时间戳

只此一种格式。历史 source/target/type、source_id/target_id、source_claim/target_claim 已废弃，build-relations.py 做了向后兼容但新写入必须用标准格式。写入路径统一用 `knowledge-ingest.py --relation`。

## 初始化

新项目首次使用时，运行一条命令完成全部初始化：

```bash
python "<skill目录>/scripts/knowledge-db-init.py" --project-path "<项目根>"
```

自动创建：SQLite 数据库 + 空 claims.jsonl + 空 relations.jsonl + config.json 模板（从 skill 目录复制）。初始化后请检查 `config.json` 中的嵌入模型配置是否符合实际环境。

## 配置

`<项目根>/knowledge-pack/config.json`：

```json
{
  "embed": {
    "base_url": "http://YOUR_EMBED_SERVER:53077/v1",
    "api_key": "sk-YOUR_KEY_HERE",
    "model": "qwen3-embed"
  }
}
```

配置优先级：config.json > 环境变量(EMBED_BASE_URL/EMBED_API_KEY/EMBED_MODEL 或 QMD_OPENAI_*) > 脚本默认值。

## 写入知识（ingest）

### 输入规范（强制）

断言 JSON 格式：

```json
{
  "statement": "一句话陈述（必填，≤200字）",
  "boundary": "成立条件（可选，强烈建议填写）",
  "source": {"id": "src:xx", "title": "来源标题", "type": "review|document|code|paper|web|expert", "url": "可选", "path": "可选，指向本地深度文件路径"},
  "confidence": 0.7,
  "characteristics": ["标签1", "标签2"]
}
```

字段约束（脚本硬校验，不合规拒绝入库）：

| 字段 | 约束 |
|---|---|
| statement | 必填，≤200字，禁含模糊词（可能/也许/或许）--模糊度用 confidence 表达 |
| boundary | 可选，留空不拒绝（但有 boundary 的断言价值更高） |
| source | 可选（AI 推理断言可无来源）；有则必须含 id+title；path 可选，指向本地 review/extract 等深度文件，检索时返回便于命中后跳转深读 |
| confidence | 0.0-1.0，默认 0.5 |
| characteristics | 标签数组，≤5个（超出自截断前5个） |

### 与外部知识结构集成时的粒度约定

当从 review/extract 等深度文件抽取断言入库时，建议每个可迁移模式（pattern）/价值主张（value_proposition）抽一条断言，避免粒度膨胀导致弱关系噪声。断言是检索入口，review 是深读目标--断言的 source.path 指向 review 文件，命中后跳转深读。

### 融合纪律（AI 必须遵守，核心约束）

**ingest 前必须先检索。禁止不查直接 ingest。**

流程：
1. **检索候选**：`knowledge-search.py --action hybrid --query "<新断言的 statement 关键词>"`，获取 Top 5 相关断言
2. **判断关系**：AI 比对新断言与每个候选，判断关系类型
3. **执行写入**：按关系类型调用 ingest 的对应参数

关系判定标准：

| 关系 | 判定条件 | 执行命令 |
|---|---|---|
| **new** | 无相关候选，或候选都不同主题 | `--claim '{...}'`（无 relation 参数） |
| **duplicate** | 与某候选语义完全相同（同主张同边界） | 不调 ingest，跳过 |
| **merge** | 与某候选同主张不同措辞 | `--claim '{...}' --merge-into CL00001` |
| **extend** | 与某候选不同边界下的补充 | `--claim '{...}' --relation extends:CL00001` |
| **conflict** | 与某候选同边界下矛盾 | `--claim '{...}' --relation opposing:CL00001` |
| **coexist** | 与某候选互补不矛盾 | `--claim '{...}' --relation coexist:CL00001` |

### 写入命令

```bash
# 新增断言（AI 判断为 new）
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." \
  --claim '{"statement":"...","boundary":"...","source":{...},"confidence":0.7,"characteristics":["..."]}'

# 批量写入
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." --claims-file claims.json

# extend CL00001
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." --claim '{...}' --relation extends:CL00001

# conflict CL00001（双方自动标 contested + 互加 opposing）
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." --claim '{...}' --relation opposing:CL00001

# merge 进 CL00001（新断言 status=merged，不参与 active 检索）
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." --claim '{...}' --merge-into CL00001
```

ingest 自动执行全链路：写 jsonl -> 更新 SQLite 索引 -> 向量嵌入 -> 构建/加载关系 -> 生成知识地图。

文件锁保护并发写入。多 subagent 并发 ingest 时自动排队等待（最多 30 秒）。

### 冲突仲裁（P0-A：opposing 闭环）

**背景**：`--relation opposing:CLxxxx` 只标记对立（双方 status=contested + opposing 互指），不裁决。**仲裁是知识演化语义的核心**——同一边界下的矛盾必须显式裁决（哪个成立/共存/无法裁决），否则 opposing 长期悬挂。

```bash
# 查看待仲裁 opposing 对（未仲裁列表）
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action arbitration --status pending

# 查看已仲裁
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action arbitration --status decided

# 仲裁一对 opposing：A 取胜，B 标 superseded（A 取代 B）
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." --arbitrate CL00001 CL00002 --arbitration-result supersede_a --arbitration-reason "理由..."

# B 取胜，A 标 superseded
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." --arbitrate CL00001 CL00002 --arbitration-result supersede_b --arbitration-reason "理由..."

# 双方保留，不同边界共存（双方 status -> active，opposing 保留但已仲裁）
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." --arbitrate CL00001 CL00002 --arbitration-result coexist --arbitration-reason "边界不同..."

# 无法裁决（双方保持 contested，等 L4 人类裁决）
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." --arbitrate CL00001 CL00002 --arbitration-result undetermined --arbitration-reason "证据不足..."
```

仲裁结果写入 `claims.jsonl` 真相源的 `arbitration` 字段（JSON 数组：target/result/decided_at/decided_by/reason）+ 更新双方 status + 写 relations.jsonl（supersedes 关系）。索引同步由脚本自动完成。

**仲裁纪律（AI 必须遵守）**：
- supersede 只用于"同一边界下新知识取代旧知识"；不同边界必须 coexist
- 无法判断时必须 undetermined（保持 contested，不假装裁决）
- 每次 consolidation 对新增 opposing 对**必须**仲裁，禁止只标不裁
- 饱和判定条件 4 要求：无未仲裁 opposing 对（`--action arbitration --status pending` 返回 0）

## 检索知识（search）

```bash
# 混合检索（FTS5+向量，首选）
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action hybrid --query "查询"

# 向量语义检索（弥合词汇差异）
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action vector --query "语义查询"

# 全文检索（FTS5 trigram 子串匹配，精确术语/ID 召回）
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action search --query "关键词"

# 关系跳转（从一条断言跳到关联断言）
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action relations --claim-id CL00001

# 按概念反查
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action concept --concept "概念名"
# concept 检索支持同义词扩展：精确匹配失败后查 concepts.aliases 模糊匹配，再 fallback characteristics LIKE
# aliases 维护：知识管理员 consolidation 时，对同义词概念（如"情景记忆/情节记忆/episodic memory"）更新 concepts.aliases 字段（JSON数组）

# 按来源反查
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action source --source-id S001

# 按状态过滤（active/contested/merged/superseded/irrelevant）
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action status --status contested

# 仲裁视图（列出 opposing 对 + 仲裁状态）
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action arbitration --status pending

# 知识库统计
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action summary
```

检索策略：
- **简单问答**：读 L0 知识概貌 -> hybrid -> 回答
- **方案设计**：hybrid -> relations -> open 深读 -> 换角度 hybrid -> 综合
- **精确术语/ID**：用 `--action search`（支持断言ID精确查询 CLxxxx，也支持关键词 FTS5 匹配）
- **按来源检索**：`--action source --source-id Sxxxx`（最可靠，一次获取同源所有断言）
- **强制规则**：所有问题必须至少一次 hybrid 或 vector 检索；不能只用一种 action 完成全部分析

### 检索决策树（什么场景用什么 action）

| 场景 | 首选 action | 补充 | 说明 |
|---|---|---|---|
| 不知道知识包有什么 | Read L0-知识概貌.md | - | 入口定位，看概念分区+全局枢纽区 |
| 已知断言ID（CLxxxx） | `search --query "CLxxxx"` | - | claim_id精确查询，不走FTS5 |
| 已知来源ID（Sxxxx） | `source --source-id Sxxxx` | - | **最可靠**，一次获取同源所有断言 |
| 已知概念名 | `concept --concept "概念名"` | - | 含aliases同义词扩展（情景记忆↔情节记忆）|
| 语义模糊查询 | `hybrid --query "查询"` | vector | FTS5+向量混合，结果看has_boundary |
| 精确关键词 | `search --query "关键词"` | - | FTS5精确匹配 |
| 找到关键断言后扩展 | `relations --claim-id CLxxxx` | - | 默认排除same_source噪声 |
| 检查知识盲区 | `leads --status open` | - | 查待跟进线索 |
| 评估知识包质量 | `health` | - | 孤儿/孤证/悬挂/一致性诊断（含未仲裁opposing/弱源高置信度） |
| 检查待仲裁冲突 | `arbitration --status pending` | - | 列出未仲裁 opposing 对（仲裁闭环入口） |
| 主题深入 | `generate-views --level L1` | - | 按需生成主题视图 |
| 核实证据细节 | Read 采录-S*.md | - | **定位后必须深读原文** |

检索机制说明：
- **hybrid** = FTS5（精确召回）+ 向量（语义召回）加权排序。FTS5命中给0.5-1.0的like_score，未命中fallback LIKE给1.0。短查询(≤4字)自动提like权重到0.6。
- **vector** = 纯向量语义检索，弥合词汇差异（搜"缺点"能找到"知识冻结"）
- **search** = FTS5精确匹配。支持断言ID（CLxxxx）精确查询、关键词FTS5匹配。claim_id是UNINDEXED，ID查询走WHERE id=?不走FTS5。
- 两者互补：向量有假阳性，FTS5 提供精确召回兜底

## 深度内容定位

断言是检索入口，source.path 指向深度文件（review/A*/C* 等）。命中断言后如需深读，用 qmd skill 在 source.path 文件内做向量检索（`qmd vsearch "断言关键词" --path <source.path>`），定位到相关段落。zhishibao 不内置文件级检索，深度定位交给 qmd（独立 skill，职责分离）。

## 知识视图

### L0 知识概貌（入口，必读）

读 `<项目根>/knowledge-pack/views/L0-知识概貌.md` 获取知识概貌（按概念分区 Top5 断言 + 全局枢纽断言 + 概念反向索引 + 关系统计 + 健康度）。ingest 后自动更新。

### L1 主题视图（按需生成）

针对某主题深入时，按需生成 L1 视图：

```bash
python "<skill目录>/scripts/generate-knowledge-views.py" --project-path "..." --level L1 --topic "主题"
```

输出 `<项目根>/knowledge-pack/views/L1-<主题>.md`，按 active/contested/merged 分组列出该主题相关断言 + 关联来源。

### 多路径兼容说明

db 检索按以下顺序查找：首选 `knowledge-pack/index/knowledge.db`（新项目标准布局）；若不存在，回退 `2-执行/03-知识提炼/`、`03-知识提炼/`（兼容历史骨架），库名兼容 `knowledge.db` 与 `knowledge-index.db`。**新项目必须用 knowledge-pack 布局**，多路径仅为兼容旧项目，未来逐步迁移后去掉。

## 线索系统（两类线索，统一查询）

知识包有**两类线索**，`--action leads` 统一查询两者：

| 类型 | 存储位置 | 产生方式 | 用途 | status值 |
|---|---|---|---|---|
| **采集线索** | source_leads 表 + source-leads.jsonl | lead-identifier.py 从A*识别 | 哪些URL/文章待采集 | pending/done/duplicate |
| **待验证方向** | leads 表 | ingest --lead 写入 | 哪些命题待验证 | open/采集中/已沉淀/放弃 |

### 查询线索

```bash
# 查所有待跟进线索（合并两个表，标注来源）
python "<skill目录>/scripts/knowledge-search.py" --project-path "..." --action leads --status open
```

结果含 `source_table` 字段标注来源（leads=待验证方向 / source_leads=采集线索）。

### 写入待验证方向

采录方（调研员/知识管理员）发现"待跟进但证据不足"的方向时，**必须**落一条 lead，不能只写在采录文件里：

```bash
python "<skill目录>/scripts/knowledge-ingest.py" --project-path "..." \
  --lead '{"target":"可验证命题","priority":"P1","reason":"为何是线索","source_id":"S0291"}'
```

线索质量要求：
- **target 必须是可验证命题**，非模糊方向（❌"研究海马体" ✅"海马体损伤是否影响情景记忆形成"）
- **priority 必须给理由**：P1=高价值待验证，P2=中等，P3=低优先

### 知识管理员 consolidation

consolidation 时，**第一件事是扫 `--action leads`**（含两类线索），决定：
- 采集线索（source_leads pending）：哪些入队 DISCOVER
- 待验证方向（leads open）：哪些已沉淀为断言（更新status）、哪些生成DISCOVER任务、哪些放弃

## 维护命令

```bash
# 手动重建索引（从 claims.jsonl 全量 upsert）
python "<skill目录>/scripts/knowledge-index-update.py" --project-path "..."

# 手动嵌入（增量，只处理无 embedding 的断言）
python "<skill目录>/scripts/embed-claims.py" --project-path "..."

# 全量重建嵌入
python "<skill目录>/scripts/embed-claims.py" --project-path "..." --full-rebuild

# 手动构建关系（加载 strong + 自动 weak）
python "<skill目录>/scripts/build-relations.py" --project-path "..."

# 手动生成 L0 知识概貌
python "<skill目录>/scripts/generate-knowledge-views.py" --project-path "..." --level L0

# 手动生成 L1 主题视图
python "<skill目录>/scripts/generate-knowledge-views.py" --project-path "..." --level L1 --topic "主题"
```

## 跨知识包检索

skill 只处理单知识包（一个 --project-path）。跨知识包检索时，AI 分别调用不同 --project-path 的 hybrid/search，自行合并去重结果。

## 核心原则

1. **先查后写**：ingest 前必须 hybrid search，禁止不查直接 ingest
2. **文件是真相源**：claims.jsonl + relations.jsonl 是真相，SQLite 是影子索引，可从 jsonl 重建
3. **边界是知识的本质**：有 boundary 的是知识，无 boundary 的是观点；boundary 提升断言价值
4. **冲突是好事**：opposing 不是判谁对谁错，是定位边界差异
5. **AI 做判断，脚本做执行**：语义融合判断（duplicate/merge/extend/conflict）由 AI 完成，脚本只执行写入+索引+嵌入
