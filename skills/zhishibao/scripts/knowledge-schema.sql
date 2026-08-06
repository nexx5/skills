-- zhishibao 知识包 Schema (V2)
-- 文件: knowledge-schema.sql
-- 用途: 定义知识包 SQLite 索引层结构
-- 设计原则: claims.jsonl 是真相源，SQLite 是影子索引（可从 jsonl 重建）
-- 四表: claims(带embedding) / sources / concepts / relations

PRAGMA journal_mode=WAL;

-- ============================================================
-- claims 表：断言（知识体系的原子单元）
-- 每条断言 = statement + boundary + source + lifecycle + embedding
-- ============================================================
CREATE TABLE IF NOT EXISTS claims (
    id              TEXT PRIMARY KEY,        -- CL00001, CL00002...
    statement       TEXT NOT NULL,            -- 断言陈述（一句话）
    boundary        TEXT,                     -- 边界条件（在什么条件下成立），可空
    source_id       TEXT,                     -- 来源ID（可空，AI推理断言可无来源）
    source_title    TEXT,                     -- 来源标题（冗余，方便展示）
    source_type     TEXT,                     -- 来源类型
    characteristics TEXT,                     -- JSON array，特点标签
    confidence      REAL DEFAULT 0.5,         -- 置信度 0.0-1.0
    extraction_level TEXT,                    -- light/deep
    status          TEXT NOT NULL DEFAULT 'active',  -- active/contested/merged/superseded/irrelevant
    opposing        TEXT,                     -- JSON array，对立断言ID列表
    possible_relations TEXT,                  -- JSON array，可能关系（文本描述）
    arbitration     TEXT,                     -- JSON array，仲裁记录：[{"target":"CLxxxx","result":"supersede|coexist|undetermined","decided_at":"ISO","decided_by":"AI|human","reason":"..."}]
    created         TEXT NOT NULL,            -- ISO date
    updated         TEXT,                     -- ISO date
    embedding       TEXT,                     -- JSON array，断言向量
    embedding_model TEXT,                     -- 嵌入模型名
    embedding_at    TEXT                      -- 嵌入时间 ISO格式
);

-- ============================================================
-- sources 表：来源元数据
-- ============================================================
CREATE TABLE IF NOT EXISTS sources (
    id              TEXT PRIMARY KEY,         -- S001, S002... 或 AI 指定的任意 id
    title           TEXT NOT NULL,
    source_type     TEXT,                     -- review/document/code/paper/web/expert/none
    url             TEXT,
    raw_path        TEXT,                     -- 原始文件相对路径（可选）
    extract_path    TEXT,                     -- 提取文件相对路径（可选）
    analysis_path   TEXT,                     -- 分析文件相对路径（可选）
    created         TEXT NOT NULL
);

-- ============================================================
-- concepts 表：概念索引（概念->断言/来源映射）
-- ============================================================
CREATE TABLE IF NOT EXISTS concepts (
    concept         TEXT NOT NULL,
    claim_ids       TEXT,                     -- JSON array of claim_id
    source_ids      TEXT,                     -- JSON array of source_id
    aliases         TEXT,                     -- JSON array of 同义词/译名，检索时模糊匹配
    PRIMARY KEY (concept)
);

-- ============================================================
-- relations 表：断言间关系
-- ============================================================
CREATE TABLE IF NOT EXISTS relations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_a         TEXT NOT NULL,
    claim_b         TEXT NOT NULL,
    relation_type   TEXT NOT NULL,            -- coexist/opposing/extends/same_source/shares_concept/alternative_to/complements/similar_to/depends_on/supersedes/upstream_of
    context         TEXT,                     -- 关系成立的上下文说明
    strength        TEXT DEFAULT 'strong',    -- strong(AI判断) / weak(算法自动)
    created         TEXT NOT NULL,
    FOREIGN KEY (claim_a) REFERENCES claims(id),
    FOREIGN KEY (claim_b) REFERENCES claims(id)
);
-- jsonl 对齐: relations.jsonl 每行 JSON 字段与本表列对齐:
--   claim_a -> claim_a, claim_b -> claim_b, relation_type -> relation_type
--   strength -> strength, context -> context, created -> created
-- 真相源是 relations.jsonl，本表是影子索引，可由 build-relations.py 从 jsonl 重建。
-- strength 取值: strong(AI判断) / medium(AI判断) / weak(算法自动 same_source/shares_concept)

CREATE INDEX IF NOT EXISTS idx_relations_a ON relations(claim_a);
CREATE INDEX IF NOT EXISTS idx_relations_b ON relations(claim_b);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_claims_source ON claims(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);

-- ============================================================
-- claims_fts 表：FTS5 全文索引
-- 新项目建库用 trigram（3字滑窗，对中文友好）；已有项目可能用 unicode61（旧schema，逐字分词）。
-- build_fts_query 已适配两者：unicode61 能处理2字中文词；trigram 对<3字报错由 try/except fallback LIKE。
-- 如需统一为 trigram，重建FTS表：DROP TABLE claims_fts; CREATE ...; INSERT INTO claims_fts(claim_id,statement,boundary,characteristics,source_title) SELECT id,statement,boundary,characteristics,source_title FROM claims;
-- 需 SQLite 3.34.0+（Python 3.10+ 自带）
-- ============================================================
CREATE VIRTUAL TABLE IF NOT EXISTS claims_fts USING fts5(
    claim_id UNINDEXED,
    statement,
    boundary,
    characteristics,
    source_title,
    tokenize='trigram'
);

-- ============================================================
-- leads 表：待跟进线索（采录时发现但未沉淀为断言的方向）
-- 采录方发现线索必须落 lead，不能只写在采录文件里（避免"搜不到=不存在"的隐性遗漏）
-- ============================================================
CREATE TABLE IF NOT EXISTS leads (
    id              TEXT PRIMARY KEY,        -- LD00001
    target          TEXT NOT NULL,           -- 线索目标（必须可验证命题，非模糊方向）
    priority        TEXT,                    -- P1/P2/P3
    reason          TEXT,                    -- 为何是线索
    source_id       TEXT,                    -- 来自哪个采录
    status          TEXT DEFAULT 'open',     -- open/采集中/已沉淀为断言/放弃
    created         TEXT NOT NULL
);
