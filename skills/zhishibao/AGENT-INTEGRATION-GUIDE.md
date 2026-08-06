# zhishibao Agent 集成指南

> 面向 agent 设计者。新建或修改 agent 时，如果该 agent 需要检索/写入知识包，照本指南配置。
> 本指南是已验证的最佳实践，基于多轮实测总结。设计者无需翻阅 SKILL.md 和各 agent 文件拼凑。

---

## 1. 什么时候用 zhishibao

agent 需要做以下任一事情时，集成 zhishibao：

- **检索知识**：从项目知识包查断言、概念、来源、关系
- **写入知识**：向知识包写入断言（ingest）
- **诊断知识包**：检查健康度、查线索

不需要 zhishibao 的场景：纯文件读写（不涉及知识包）、纯计算、纯外部搜索。

---

## 2. 权限配置

agent 的 AGENTS.md 头部 permission 必须加：

```yaml
permission:
  skill:
    "zhishibao": allow
    "qmd": allow   # 深读文件时用 qmd 语义检索（可选）
    "*": deny
```

agent 调用方式：读 SKILL.md 获取用法规范，用 bash 跑 `python <skill目录>/scripts/xxx.py --project-path "..." --action ...`。

---

## 3. AGENTS.md 必须包含的三块内容

### 3.1 检索工具表（直接抄，按需删减）

```markdown
| 工具 | skill action | 作用 | 使用时机 |
|---|---|---|---|
| **L0知识概貌** | Read `views/L0-知识概貌.md` | 入口定位：概念分区+全局枢纽断言区 | **必须第一步** |
| **L1主题视图** | `generate-knowledge-views.py --level L1 --topic "主题"` | 按主题深入 | 主题明确时按需生成 |
| **hybrid** | `--action hybrid --query "查询"` | FTS5+向量混合，结果含has_boundary | 复杂问题首选 |
| **vector** | `--action vector --query "语义查询"` | 纯向量语义 | hybrid无结果时 |
| **search** | `--action search --query "关键词或CLxxxx"` | FTS5精确匹配+断言ID精确查询 | 已知精确术语或断言ID时 |
| **relations** | `--action relations --claim-id CLxxxx` | 关系跳转。默认排除same_source噪声 | 找到关键断言后**必须**扩展 |
| **concept** | `--action concept --concept "概念名"` | 按概念反查，含同义词扩展 | 按主题定位时 |
| **source** | `--action source --source-id Sxxxx` | 按来源反查全部断言。**最可靠** | 追溯来源时 |
| **leads** | `--action leads --status open` | 查待跟进线索（采集线索+待验证方向） | 检查知识盲区时 |
| **health** | `--action health` | 知识包健康诊断 | 评估质量时 |
| **open** | Read 采录/分析文件 | 深读原文。看has_boundary字段 | 定位后**必须**深读 |
```

### 3.2 检索流程（直接抄）

```markdown
Level 0: 读L0知识概貌 -> 定位主题+全局枢纽断言

Level 1: 语义检索（必须）
         hybrid(查询) -> FTS5+向量混合

Level 2: 精确检索（必须，不能跳过）
         search(关键词) + concept(概念名)

Level 3: 关系跳转（必须，不能跳过）
         relations(断言ID) -> 扩展关联断言

Level 4: 深读（必须，不能跳过）
         Read 采录/A*/C*文件 -> 核实原文

Level 5: 压缩 -> 保留结论+断言ID

强制规则：
1. 每轮至少用3种action（不能只用hybrid）
2. Level 2-4 不可跳过
3. 深读必须读采录原文（断言级信息是压缩的）
4. 检索结果看has_boundary字段（有边界=知识，无边界=观点）
```

### 3.3 检索纪律（直接抄）

```markdown
1. 检索走 zhishibao skill，深读走 Read（禁止 glob+grep 遍历数据文件）
2. 禁止直接写 SQL（用 action 替代）
3. 来源区分必须诚实：hybrid检索结果、schools.jsonl读取、source反查必须分别标注，不能混称"检索结果"
4. 不能用单一action完成全部分析
```

---

## 4. 检索决策树（什么场景用什么）

| 场景 | 首选 | 说明 |
|---|---|---|
| 不知道知识包有什么 | Read L0 | 入口，看概念分区+枢纽区 |
| 已知断言ID | `search "CLxxxx"` | 精确查询，不走FTS5 |
| 已知来源ID | `source --source-id Sxxxx` | **最可靠**，一次获取同源全部断言 |
| 已知概念名 | `concept --concept "名"` | 含同义词扩展 |
| 语义模糊查询 | `hybrid --query "查询"` | FTS5+向量，看has_boundary |
| 精确关键词 | `search --query "词"` | FTS5匹配 |
| 关键断言扩展 | `relations --claim-id CLxxxx` | 默认排除same_source |
| 检查知识盲区 | `leads --status open` | 合并查采集线索+待验证方向 |
| 评估质量 | `health` | 9项诊断 |
| 主题深入 | `generate-views --level L1` | 按需生成 |
| 核实证据 | Read 采录文件 | **必须深读原文** |

---

## 5. 写入约束（仅知识管理员需要）

如果 agent 需要写入断言（ingest），必须遵守：

### 融合纪律（强制）
1. **ingest 前必须先检索**：`hybrid --query "<新断言关键词>"` 查候选
2. 判断关系：new/duplicate/merge/extend/conflict/coexist
3. 按关系执行写入

### 数据安全
- ingest 有 jsonl/SQLite 一致性校验（jsonl空但SQLite有数据时拒绝写入）
- claims.jsonl 是真相源，SQLite 是影子索引（可重建）
- 文件锁保护并发写入

### 线索写入
- 发现待验证方向时用 `ingest --lead '{"target":"可验证命题","priority":"P1","reason":"...","source_id":"Sxxxx"}'`
- target 必须是可验证命题，非模糊方向

---

## 6. 常见错误（实测总结，避免重蹈）

| 错误 | 后果 | 正确做法 |
|---|---|---|
| 只用hybrid一种action | 召回不足、漏关键断言 | 每轮≥3种action（hybrid+relations+source等）|
| 不深读采录文件 | 证据深度不够、引用不精确 | 定位后必须Read原文核实 |
| 把schools.jsonl数据描述为"检索结果" | 诚信瑕疵 | 严格区分来源，分别标注 |
| 直接写SQL查SQLite | 绕过向量检索/关系跳转 | 用action替代 |
| glob+grep遍历数据文件 | 绕过语义检索 | 用action替代 |
| 忘记看has_boundary | 混淆知识和观点 | 有边界=知识，无边界=观点 |
| relations只看strong | 漏shares_concept等weak关系 | 默认all+exclude same_source |

---

## 7. 关键参数速查

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--strength` | all | relations强度过滤（默认查全部） |
| `--exclude-types` | same_source | relations排除的关系类型（默认排除同源噪声）|
| `--limit` | 20 | 返回条数上限 |
| `--status` | open(leads) / 无(claims) | leads查open，claims status查指定状态 |
| hybrid权重 | like:0.4/vector:0.6 | config.json可配；短查询(≤4字)自动提like到0.6 |

---

## 8. 知识包结构速查

```
<项目>/knowledge-pack/
├── claims.jsonl        # 断言真相源（每行一条JSON）
├── relations.jsonl     # AI手建的strong关系
├── source-leads.jsonl  # 采集线索池（URL列表）
├── schools.jsonl       # 流派定义
├── config.json         # 嵌入模型配置 + 检索权重
├── index/knowledge.db  # SQLite影子索引（可从jsonl重建）
└── views/
    ├── L0-知识概貌.md   # 入口视图（自动生成）
    └── L1-*.md          # 主题视图（按需生成）
```

---

## 9. 检查清单（设计agent时逐项确认）

- [ ] permission 加了 `"zhishibao": allow`
- [ ] AGENTS.md 有检索工具表（含全部10种action）
- [ ] AGENTS.md 有检索流程（Level 0-5，强制规则）
- [ ] AGENTS.md 有检索纪律（来源区分、多action、深读）
- [ ] 如果写入断言：有融合纪律（先查后写）
- [ ] 如果是知识管理员：有leads查询+health检查流程
