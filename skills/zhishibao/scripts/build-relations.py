#!/usr/bin/env python3
"""
关系构建与路径回填脚本：consolidation时调用。
1. 加载 relations.jsonl 的人工 strong/medium 关系到 SQLite（真相源 -> 影子索引）
2. 构建 same_source 关系（同源断言间自动建边，weak）
3. 构建 shares_concept 关系（共享低频概念的断言间建边，weak）
4. 回填 sources 表的 raw_path / extract_path 字段
5. --check 模式：对比 jsonl vs SQLite，报告不一致

兼容三种历史字段名：
  claim_a/claim_b/relation_type (标准)
  source_id/target_id/relation_type (旧格式)
  source/target/type (更旧格式)

用法：
    python build-relations.py --project-path "..."
    python build-relations.py --project-path "..." --relations-only
    python build-relations.py --project-path "..." --paths-only
    python build-relations.py --project-path "..." --check
    python build-relations.py --project-path "..." --skip-manual
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from itertools import combinations

# Windows PowerShell GBK编码修复：强制stdout用UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def get_db_conn(project_path: str) -> sqlite3.Connection:
    for candidate in ['knowledge-pack/index', '2-执行/03-知识提炼', '03-知识提炼']:
        for db_name in ['knowledge.db', 'knowledge-index.db']:
            db_path = os.path.join(project_path, candidate, db_name)
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                return conn
    print(f"ERROR: 找不到 DB", file=sys.stderr)
    sys.exit(1)


def ensure_columns(conn):
    """确保 relations 表有 strength 列"""
    cursor = conn.execute("PRAGMA table_info(relations)")
    cols = {row[1] for row in cursor.fetchall()}
    if 'strength' not in cols:
        conn.execute("ALTER TABLE relations ADD COLUMN strength TEXT DEFAULT 'strong'")
        conn.commit()
        print("  已添加 relations.strength 列")


# ============================================================
# 常量
# ============================================================

LOW_FREQ_THRESHOLD = 5     # 关联<5条断言的概念为低频
MID_FREQ_THRESHOLD = 50    # 关联≥50条断言的概念为高频，不用于shares_concept
MAX_SAME_SOURCE_PAIRS = 8  # 同源断言超过8条时只取前8条两两建边


# ============================================================
# 人工关系加载（jsonl -> SQLite）
# ============================================================

def load_strong_relations_from_jsonl(conn, project_path):
    """
    从 relations.jsonl（真相源）加载 strong/medium 关系到 SQLite。

    兼容三种历史字段名（A1）：
      claim_a/claim_b/relation_type (标准)
      source_id/target_id/relation_type (旧格式)
      source/target/type (更旧格式)

    支持 strength: strong, medium（A2）
    claim 存在性校验: dangling 关系打 WARNING 并跳过（A3）

    返回: (added, updated, skipped_unknown, skipped_strength, dangling)
    """
    rel_path = os.path.join(project_path, 'knowledge-pack', 'relations.jsonl')
    if not os.path.exists(rel_path):
        return 0, 0, 0, 0, 0

    # 获取所有 claim IDs（用于存在性校验）
    claim_ids = {row[0] for row in conn.execute("SELECT id FROM claims").fetchall()}

    added = 0
    updated = 0
    skipped_unknown = 0    # 字段名不识别或 JSON 解析失败
    skipped_strength = 0   # strength 不是 strong/medium
    dangling = 0           # claim 不存在

    with open(rel_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rel = json.loads(line)
            except json.JSONDecodeError:
                skipped_unknown += 1
                continue

            # A1: 字段名四层 fallback（含 source_claim/target_claim）
            a = rel.get('claim_a') or rel.get('source_id') or rel.get('source') or rel.get('source_claim')
            b = rel.get('claim_b') or rel.get('target_id') or rel.get('target') or rel.get('target_claim')
            rtype = rel.get('relation_type') or rel.get('type')

            if not a or not b or not rtype:
                skipped_unknown += 1
                continue

            # A2: medium 支持
            strength = rel.get('strength', 'strong')
            if strength not in ('strong', 'medium'):
                skipped_strength += 1
                continue

            # A3: claim 存在性校验
            if a not in claim_ids or b not in claim_ids:
                dangling += 1
                print(f"  WARNING: dangling relation {a} --{rtype}--> {b} (claim 不存在)", file=sys.stderr)
                continue

            context = rel.get('context', '')
            created = rel.get('created', datetime.now(timezone.utc).isoformat())

            # upsert (按 claim_a + claim_b + relation_type + strength 去重)
            exists = conn.execute(
                "SELECT id FROM relations WHERE claim_a=? AND claim_b=? AND relation_type=? AND strength=?",
                (a, b, rtype, strength)
            ).fetchone()

            if exists:
                conn.execute(
                    "UPDATE relations SET context=?, created=? WHERE id=?",
                    (context, created, exists['id'])
                )
                updated += 1
            else:
                conn.execute(
                    "INSERT INTO relations (claim_a, claim_b, relation_type, context, strength, created) VALUES (?, ?, ?, ?, ?, ?)",
                    (a, b, rtype, context, strength, created)
                )
                added += 1

    conn.commit()
    return added, updated, skipped_unknown, skipped_strength, dangling


# ============================================================
# 一致性检查（--check 模式）
# ============================================================

def check_consistency(conn, project_path):
    """
    对比 relations.jsonl vs SQLite relations 表，报告不一致。
    不写数据，只报告。

    返回: (forward_missing, reverse_missing, dangling)
    """
    rel_path = os.path.join(project_path, 'knowledge-pack', 'relations.jsonl')

    # 获取 claim IDs
    claim_ids = {row[0] for row in conn.execute("SELECT id FROM claims").fetchall()}

    # 读取 jsonl（兼容三种字段名）
    jsonl_rels = set()  # (claim_a, claim_b, relation_type, strength)
    jsonl_strong = 0
    jsonl_medium = 0
    dangling = 0

    if os.path.exists(rel_path):
        with open(rel_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rel = json.loads(line)
                except json.JSONDecodeError:
                    continue

                a = rel.get('claim_a') or rel.get('source_id') or rel.get('source') or rel.get('source_claim')
                b = rel.get('claim_b') or rel.get('target_id') or rel.get('target') or rel.get('target_claim')
                rtype = rel.get('relation_type') or rel.get('type')
                strength = rel.get('strength', 'strong')

                if not a or not b or not rtype:
                    continue
                if strength not in ('strong', 'medium'):
                    continue
                if a not in claim_ids or b not in claim_ids:
                    dangling += 1
                    continue

                jsonl_rels.add((a, b, rtype, strength))
                if strength == 'strong':
                    jsonl_strong += 1
                else:
                    jsonl_medium += 1

    # 获取 SQLite 中的 strong/medium 关系
    sqlite_rels = set()
    sqlite_strong = 0
    sqlite_medium = 0

    for row in conn.execute(
        "SELECT claim_a, claim_b, relation_type, strength FROM relations WHERE strength IN ('strong', 'medium')"
    ).fetchall():
        key = (row['claim_a'], row['claim_b'], row['relation_type'], row['strength'])
        sqlite_rels.add(key)
        if row['strength'] == 'strong':
            sqlite_strong += 1
        else:
            sqlite_medium += 1

    # 正向脱库: jsonl 有但 SQLite 没有（考虑双向 claim_a<->claim_b）
    forward_missing = set()
    for r in jsonl_rels:
        rev = (r[1], r[0], r[2], r[3])
        if r not in sqlite_rels and rev not in sqlite_rels:
            forward_missing.add(r)

    # 反向脱库: SQLite 有但 jsonl 没有（考虑双向）
    reverse_missing = set()
    for r in sqlite_rels:
        rev = (r[1], r[0], r[2], r[3])
        if r not in jsonl_rels and rev not in jsonl_rels:
            reverse_missing.add(r)

    print("=== 一致性检查 ===")
    print(f"  jsonl 关系: {len(jsonl_rels)} (strong={jsonl_strong}, medium={jsonl_medium})")
    print(f"  SQLite 关系: {len(sqlite_rels)} (strong={sqlite_strong}, medium={sqlite_medium})")
    print(f"  正向脱库 (jsonl 有 SQLite 无): {len(forward_missing)}")
    print(f"  反向脱库 (SQLite 有 jsonl 无): {len(reverse_missing)}")
    print(f"  dangling (claim 不存在): {dangling}")

    if forward_missing:
        print("  正向脱库明细 (前10条):")
        for r in sorted(forward_missing)[:10]:
            print(f"    {r[0]} --{r[2]}({r[3]})--> {r[1]}")

    if reverse_missing:
        print("  反向脱库明细 (前10条):")
        for r in sorted(reverse_missing)[:10]:
            print(f"    {r[0]} --{r[2]}({r[3]})--> {r[1]}")

    return len(forward_missing), len(reverse_missing), dangling


# ============================================================
# 自动关系构建
# ============================================================

def build_same_source_relations(conn):
    """构建 same_source 关系：同一来源的断言间建 weak 边"""
    now = datetime.now(timezone.utc).isoformat()
    added = 0

    rows = conn.execute("SELECT id, source_id FROM claims WHERE source_id IS NOT NULL AND source_id != ''").fetchall()

    source_to_claims = {}
    for row in rows:
        sid = row['source_id']
        source_to_claims.setdefault(sid, []).append(row['id'])

    existing = set()
    for r in conn.execute("SELECT claim_a, claim_b, relation_type FROM relations WHERE relation_type='same_source'").fetchall():
        existing.add((r['claim_a'], r['claim_b']))

    for source_id, claim_ids in source_to_claims.items():
        if len(claim_ids) < 2:
            continue
        if len(claim_ids) > MAX_SAME_SOURCE_PAIRS:
            claim_ids = claim_ids[:MAX_SAME_SOURCE_PAIRS]

        for a, b in combinations(sorted(claim_ids), 2):
            if (a, b) not in existing and (b, a) not in existing:
                conn.execute(
                    "INSERT INTO relations (claim_a, claim_b, relation_type, context, strength, created) VALUES (?, ?, ?, ?, ?, ?)",
                    (a, b, 'same_source', f'同来源 {source_id}', 'weak', now)
                )
                existing.add((a, b))
                added += 1

    conn.commit()
    return added


def build_shares_concept_relations(conn):
    """构建 shares_concept 关系：共享低频概念的断言间建 weak 边"""
    now = datetime.now(timezone.utc).isoformat()
    added = 0

    concept_rows = conn.execute("SELECT concept, claim_ids FROM concepts WHERE claim_ids IS NOT NULL AND claim_ids != ''").fetchall()

    concept_freq = {}
    for row in concept_rows:
        try:
            cids = json.loads(row['claim_ids'])
        except (json.JSONDecodeError, TypeError):
            continue
        if len(cids) >= 2:
            concept_freq[row['concept']] = cids

    low_freq_concepts = {c: cids for c, cids in concept_freq.items() if len(cids) < LOW_FREQ_THRESHOLD}
    mid_freq_concepts = {c: cids for c, cids in concept_freq.items() if LOW_FREQ_THRESHOLD <= len(cids) < MID_FREQ_THRESHOLD}

    print(f"  概念频率分布: 低频(直接建边)={len(low_freq_concepts)}, 中频(需共享≥2)={len(mid_freq_concepts)}, 高频(跳过)={len(concept_freq) - len(low_freq_concepts) - len(mid_freq_concepts)}")

    existing = set()
    for r in conn.execute("SELECT claim_a, claim_b FROM relations WHERE relation_type='shares_concept'").fetchall():
        existing.add((r['claim_a'], r['claim_b']))

    # 低频概念：共享1个就建边
    for concept, cids in low_freq_concepts.items():
        if len(cids) < 2:
            continue
        for a, b in combinations(sorted(cids), 2):
            if (a, b) not in existing and (b, a) not in existing:
                conn.execute(
                    "INSERT INTO relations (claim_a, claim_b, relation_type, context, strength, created) VALUES (?, ?, ?, ?, ?, ?)",
                    (a, b, 'shares_concept', f'共享低频概念: {concept}', 'weak', now)
                )
                existing.add((a, b))
                added += 1

    # 中频概念：需要两条断言共享≥2个中频概念才建边
    claim_to_mid_concepts = {}
    for concept, cids in mid_freq_concepts.items():
        for cid in cids:
            claim_to_mid_concepts.setdefault(cid, set()).add(concept)

    mid_pairs = {}
    for concept, cids in mid_freq_concepts.items():
        if len(cids) < 2:
            continue
        if len(cids) > 100:
            cids = cids[:100]
        for a, b in combinations(sorted(cids), 2):
            key = (a, b)
            mid_pairs[key] = mid_pairs.get(key, 0) + 1

    for (a, b), count in mid_pairs.items():
        if count >= 2 and (a, b) not in existing and (b, a) not in existing:
            shared = claim_to_mid_concepts.get(a, set()) & claim_to_mid_concepts.get(b, set())
            conn.execute(
                "INSERT INTO relations (claim_a, claim_b, relation_type, context, strength, created) VALUES (?, ?, ?, ?, ?, ?)",
                (a, b, 'shares_concept', f'共享{count}个中频概念: {", ".join(list(shared)[:3])}', 'weak', now)
            )
            existing.add((a, b))
            added += 1

    conn.commit()
    return added


# ============================================================
# 路径回填
# ============================================================

def backfill_source_paths(conn, project_path):
    """回填 sources 表的 raw_path / extract_path 字段"""
    updated = 0

    raw_dirs = [
        os.path.join(project_path, 'knowledge-pack', 'raw', 'local'),
        os.path.join(project_path, 'knowledge-pack', 'raw', 'web'),
        os.path.join(project_path, '2-执行', '01-采集记录', '原始资料'),
    ]
    evidence_dirs = [
        os.path.join(project_path, 'knowledge-pack', 'evidence'),
        os.path.join(project_path, '2-执行', '01-采集记录'),
    ]

    rows = conn.execute("SELECT id FROM sources").fetchall()

    for row in rows:
        sid = row['id']
        raw_path = None
        extract_path = None

        for d in raw_dirs:
            for pattern in [f'raw-{sid}.md', f'{sid}.md']:
                p = os.path.join(d, pattern)
                if os.path.exists(p):
                    raw_path = os.path.relpath(p, project_path)
                    break
            if raw_path:
                break

        for d in evidence_dirs:
            for pattern in [f'采录-{sid}.md', f'采集记录-{sid}.md', f'{sid}.md']:
                p = os.path.join(d, pattern)
                if os.path.exists(p):
                    extract_path = os.path.relpath(p, project_path)
                    break
            if extract_path:
                break

        if raw_path or extract_path:
            conn.execute("UPDATE sources SET raw_path = ?, extract_path = ? WHERE id = ?",
                         (raw_path, extract_path, sid))
            updated += 1

    conn.commit()
    return updated


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='关系构建与路径回填')
    parser.add_argument('--project-path', required=True, help='项目根目录路径')
    parser.add_argument('--relations-only', action='store_true', help='只构建关系，不回填路径')
    parser.add_argument('--paths-only', action='store_true', help='只回填路径，不构建关系')
    parser.add_argument('--check', action='store_true', help='对比 jsonl vs SQLite，不写数据')
    parser.add_argument('--skip-manual', action='store_true', help='跳过 jsonl 加载，只构建自动关系')
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    conn = get_db_conn(project_path)
    ensure_columns(conn)

    # --check 模式：只报告，不写数据
    if args.check:
        check_consistency(conn, project_path)
        conn.close()
        print("完成。")
        return

    do_relations = not args.paths_only
    do_paths = not args.relations_only

    if do_relations:
        if not args.skip_manual:
            print("=== 加载 relations.jsonl 关系（真相源） ===")
            added, updated, skipped_unknown, skipped_strength, dangling = \
                load_strong_relations_from_jsonl(conn, project_path)
            print(f"  新增: {added}, 更新: {updated}")
            print(f"  跳过(字段名不识别): {skipped_unknown}")
            print(f"  跳过(strength非strong/medium): {skipped_strength}")
            print(f"  跳过(dangling/claim不存在): {dangling}")
        else:
            print("=== 跳过 jsonl 加载 (--skip-manual) ===")

        print("=== 构建 same_source 关系 ===")
        ss_count = build_same_source_relations(conn)
        print(f"  新增 same_source 关系: {ss_count}")

        print("=== 构建 shares_concept 关系 ===")
        sc_count = build_shares_concept_relations(conn)
        print(f"  新增 shares_concept 关系: {sc_count}")

        total = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
        weak = conn.execute("SELECT COUNT(*) FROM relations WHERE strength='weak'").fetchone()[0]
        strong = conn.execute("SELECT COUNT(*) FROM relations WHERE strength='strong'").fetchone()[0]
        medium = conn.execute("SELECT COUNT(*) FROM relations WHERE strength='medium'").fetchone()[0]
        print(f"  关系总计: {total} (weak={weak}, strong={strong}, medium={medium})")

    if do_paths:
        print("=== 回填 sources 表路径 ===")
        path_count = backfill_source_paths(conn, project_path)
        print(f"  更新路径: {path_count}")

    conn.close()
    print("完成。")


if __name__ == '__main__':
    main()
