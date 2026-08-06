#!/usr/bin/env python3
"""
zhishibao 知识包索引更新 - knowledge-index-update.py
功能：从 claims.jsonl 全量 upsert 到 SQLite（claims/sources/concepts）
使用：python knowledge-index-update.py --project-path "<项目路径>"
设计：claims.jsonl 是真相源，本脚本同步到 SQLite 影子索引，保留已有 embedding
"""

import sqlite3
import json
import argparse
import os
import sys
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def get_db_conn(project_path):
    db_path = os.path.join(project_path, 'knowledge-pack', 'index', 'knowledge.db')
    if not os.path.exists(db_path):
        print(f"ERROR: knowledge.db 不存在: {db_path}", file=sys.stderr)
        print(f"  请先运行 knowledge-db-init.py", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def read_jsonl(jsonl_path):
    """读取全部 claims.jsonl"""
    claims = []
    if not os.path.exists(jsonl_path):
        return claims
    with open(jsonl_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                claims.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return claims


def ensure_arbitration_col(conn):
    """兼容旧库：claims 表无 arbitration 列时 ALTER TABLE 添加（SQLite 支持 ADD COLUMN）"""
    cursor = conn.execute("PRAGMA table_info(claims)")
    cols = {row[1] for row in cursor.fetchall()}
    if 'arbitration' not in cols:
        conn.execute("ALTER TABLE claims ADD COLUMN arbitration TEXT")
        conn.commit()


def upsert_claims(conn, claims):
    """逐条 upsert claims，保留已有 embedding"""
    added = 0
    updated = 0
    now = datetime.now(timezone.utc).isoformat()
    ensure_arbitration_col(conn)

    for claim in claims:
        cid = claim.get('claim_id') or claim.get('id')
        if not cid:
            continue

        source = claim.get('source', {}) or {}
        characteristics = json.dumps(claim.get('characteristics', []), ensure_ascii=False)
        opposing = json.dumps(claim.get('opposing', []), ensure_ascii=False)
        possible_relations = json.dumps(claim.get('possible_relations', []), ensure_ascii=False)
        arbitration = json.dumps(claim.get('arbitration', []), ensure_ascii=False)
        created = claim.get('created', now)

        existing = conn.execute("SELECT id, embedding, embedding_model, embedding_at FROM claims WHERE id = ?", (cid,)).fetchone()

        if existing:
            # 更新，但保留 embedding
            conn.execute("""
                UPDATE claims SET statement=?, boundary=?, source_id=?, source_title=?,
                source_type=?, characteristics=?, confidence=?,
                extraction_level=?, status=?, opposing=?, possible_relations=?, arbitration=?, updated=?
                WHERE id=?
            """, (
                claim.get('statement', ''), claim.get('boundary', ''),
                source.get('id', ''), source.get('title', ''), source.get('type', ''),
                characteristics, claim.get('confidence', 0.5),
                claim.get('extraction_level', 'deep'), claim.get('status', 'active'),
                opposing, possible_relations, arbitration, now, cid
            ))
            updated += 1
        else:
            conn.execute("""
                INSERT INTO claims (id, statement, boundary, source_id, source_title,
                source_type, characteristics, confidence, extraction_level,
                status, opposing, possible_relations, arbitration, created, updated)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                cid, claim.get('statement', ''), claim.get('boundary', ''),
                source.get('id', ''), source.get('title'), source.get('type', ''),
                characteristics, claim.get('confidence', 0.5),
                claim.get('extraction_level', 'deep'), claim.get('status', 'active'),
                opposing, possible_relations, arbitration, created, created
            ))
            added += 1

        # 同步 FTS5 索引（先删后插）
        try:
            conn.execute("DELETE FROM claims_fts WHERE claim_id = ?", (cid,))
            conn.execute("""
                INSERT INTO claims_fts (claim_id, statement, boundary, characteristics, source_title)
                VALUES (?,?,?,?,?)
            """, (
                cid, claim.get('statement', ''), claim.get('boundary', ''),
                characteristics, source.get('title', '')
            ))
        except sqlite3.OperationalError:
            pass

    conn.commit()
    return added, updated


def upsert_sources(conn, claims):
    """从 claims 的 source 字段提取并 upsert sources"""
    added = 0
    now = datetime.now(timezone.utc).isoformat()

    seen = set()
    for claim in claims:
        source = claim.get('source', {}) or {}
        sid = source.get('id')
        if not sid or sid in seen:
            continue
        seen.add(sid)

        existing = conn.execute("SELECT id FROM sources WHERE id = ?", (sid,)).fetchone()
        if not existing:
            conn.execute("""
                INSERT OR IGNORE INTO sources (id, title, source_type, url, created)
                VALUES (?,?,?,?,?)
            """, (
                sid, source.get('title', ''), source.get('type', ''),
                source.get('url', ''), now
            ))
            added += 1

    conn.commit()
    return added


def rebuild_concepts(conn, claims):
    """从 claims 的 characteristics 全量重建 concepts 表"""
    conn.execute("DELETE FROM concepts")

    concept_map = {}  # concept -> {claim_ids: set, source_ids: set}
    for claim in claims:
        cid = claim.get('claim_id') or claim.get('id')
        if not cid:
            continue
        chars = claim.get('characteristics', [])
        source = claim.get('source', {}) or {}
        sid = source.get('id', '')

        for char in chars:
            if char not in concept_map:
                concept_map[char] = {'claim_ids': set(), 'source_ids': set()}
            concept_map[char]['claim_ids'].add(cid)
            if sid:
                concept_map[char]['source_ids'].add(sid)

    now = datetime.now(timezone.utc).isoformat()
    for concept, data in concept_map.items():
        conn.execute("""
            INSERT INTO concepts (concept, claim_ids, source_ids) VALUES (?,?,?)
        """, (
            concept,
            json.dumps(sorted(data['claim_ids']), ensure_ascii=False),
            json.dumps(sorted(data['source_ids']), ensure_ascii=False)
        ))

    conn.commit()
    return len(concept_map)


def main():
    parser = argparse.ArgumentParser(description='zhishibao 知识包索引更新')
    parser.add_argument('--project-path', required=True, help='项目根目录路径')
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    jsonl_path = os.path.join(project_path, 'knowledge-pack', 'claims.jsonl')

    print(f"项目: {project_path}")

    claims = read_jsonl(jsonl_path)
    print(f"读取 claims.jsonl: {len(claims)} 条")

    conn = get_db_conn(project_path)

    print("=== upsert claims ===")
    added, updated = upsert_claims(conn, claims)
    print(f"  新增: {added}, 更新: {updated}")

    print("=== upsert sources ===")
    src_added = upsert_sources(conn, claims)
    print(f"  新增来源: {src_added}")

    print("=== 重建 concepts ===")
    concept_count = rebuild_concepts(conn, claims)
    print(f"  概念数: {concept_count}")

    total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM claims WHERE status='active'").fetchone()[0]
    print(f"\n完成。断言总计: {total} (active: {active})")

    conn.close()


if __name__ == '__main__':
    main()
