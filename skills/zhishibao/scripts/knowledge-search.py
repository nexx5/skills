#!/usr/bin/env python3
"""
zhishibao 知识检索 - knowledge-search.py
功能：封装 SQLite 检索操作，供 AI 通过 bash 调用
支持：search(LIKE) / vector(向量语义) / hybrid(混合) / status / source / concept / relations / summary
使用：
    python knowledge-search.py --project-path "..." --action hybrid --query "查询"
    python knowledge-search.py --project-path "..." --action relations --claim-id CL00001
配置优先级：config.json > 环境变量 > 默认值
"""

import argparse
import json
import math
import os
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# numpy 可选--有则矩阵化加速（1034ms->4ms），无则降级纯Python
try:
    import numpy as _np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


# ============================================================
# embedding 矩阵持久化缓存（性能优化：1034ms -> ~100ms）
# ============================================================
# 瓶颈定位：纯Python逐条json.loads+cosine 4456条=1034ms。
# numpy矩阵化:matmul 4ms,但构建矩阵(json.loads 4456次+np.array)=861ms。
# 持久化缓存到磁盘(.npy+meta.json):首次构建861ms,后续读盘~80ms+matmul 4ms≈100ms。
# 指纹=total_claims:count_with_emb:max_embedding_at,变化才重建。
# 文件是真相源,SQLite是影子,本缓存是影子的影子--可随时删除重建。

_EMB_CACHE = {'matrix': None, 'ids': None, 'fingerprint': None, 'norms': None}


def _embedding_fingerprint(conn):
    """指纹:claims总数+有embedding数+最大embedding_at"""
    total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    emb_row = conn.execute(
        "SELECT COUNT(*), MAX(embedding_at) FROM claims WHERE embedding IS NOT NULL AND embedding != ''"
    ).fetchone()
    return f"{total}:{emb_row[0]}:{emb_row[1] or ''}"


def _load_embedding_matrix(conn, project_path):
    """加载归一化后的embedding矩阵(带持久化缓存)。返回 (matrix, ids) 或 (None, None)。"""
    if not _HAS_NUMPY:
        return None, None
    fp = _embedding_fingerprint(conn)
    # 进程内缓存命中
    if _EMB_CACHE['matrix'] is not None and _EMB_CACHE['fingerprint'] == fp:
        return _EMB_CACHE['matrix'], _EMB_CACHE['ids']

    # 磁盘缓存
    cache_dir = os.path.join(project_path, 'knowledge-pack', 'index')
    npy_path = os.path.join(cache_dir, 'embedding_matrix.npy')
    meta_path = os.path.join(cache_dir, 'embedding_meta.json')
    if os.path.exists(npy_path) and os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            if meta.get('fingerprint') == fp:
                matrix = _np.load(npy_path, allow_pickle=False)
                ids = meta.get('ids', [])
                if matrix.shape[0] == len(ids) and len(ids) > 0:
                    # 预计算归一化矩阵(cosine=dot)
                    norms = _np.linalg.norm(matrix, axis=1, keepdims=True)
                    norms[norms == 0] = 1.0
                    normed = matrix / norms
                    _EMB_CACHE['matrix'] = normed
                    _EMB_CACHE['ids'] = ids
                    _EMB_CACHE['fingerprint'] = fp
                    return normed, ids
        except Exception:
            pass  # 缓存损坏->重建

    # 构建(冷启动)
    rows = conn.execute(
        "SELECT id, embedding FROM claims WHERE embedding IS NOT NULL AND embedding != '' ORDER BY id"
    ).fetchall()
    if not rows:
        return None, None
    ids = [r['id'] for r in rows]
    try:
        matrix = _np.array([json.loads(r['embedding']) for r in rows], dtype=_np.float32)
    except (json.JSONDecodeError, ValueError):
        return None, None
    norms = _np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normed = matrix / norms

    # 持久化
    try:
        os.makedirs(cache_dir, exist_ok=True)
        _np.save(npy_path, normed, allow_pickle=False)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({'fingerprint': fp, 'ids': ids, 'count': len(ids)}, f, ensure_ascii=False)
    except Exception:
        pass  # 写盘失败不影响内存使用

    _EMB_CACHE['matrix'] = normed
    _EMB_CACHE['ids'] = ids
    _EMB_CACHE['fingerprint'] = fp
    return normed, ids


# ============================================================
# 配置读取
# ============================================================

def load_embed_config(project_path):
    config_path = os.path.join(project_path, 'knowledge-pack', 'config.json')
    base_url = os.environ.get('EMBED_BASE_URL') or os.environ.get('QMD_OPENAI_BASE_URL') or 'http://YOUR_EMBED_SERVER:7307/v1'
    api_key = os.environ.get('EMBED_API_KEY') or os.environ.get('QMD_OPENAI_API_KEY') or 'sk-default'
    model = os.environ.get('EMBED_MODEL') or os.environ.get('QMD_EMBED_MODEL') or 'qwen3-embed'

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        embed = cfg.get('embed', {})
        if embed.get('base_url'):
            base_url = embed['base_url']
        if embed.get('api_key'):
            api_key = embed['api_key']
        if embed.get('model'):
            model = embed['model']

    return base_url, api_key, model


def load_search_weights(project_path):
    """读取 hybrid 检索权重配置（config.json > 默认值）"""
    default = {'like': 0.4, 'vector': 0.6, 'auto_boost_short_query': True, 'short_query_threshold': 4}
    config_path = os.path.join(project_path, 'knowledge-pack', 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        sw = cfg.get('search_weights', {})
        default.update(sw)
    return default


def get_db_conn(project_path):
    for candidate in ['knowledge-pack/index', '2-执行/03-知识提炼', '03-知识提炼']:
        for db_name in ['knowledge.db', 'knowledge-index.db']:
            db_path = os.path.join(project_path, candidate, db_name)
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                return conn
    print(json.dumps({"error": "knowledge.db/knowledge-index.db 不存在", "hint": "请先运行 knowledge-db-init.py", "project_path": project_path}, ensure_ascii=False))
    sys.exit(1)


def fmt_row(row):
    d = {k: row[k] for k in row.keys()}
    d['has_boundary'] = bool(d.get('boundary'))
    # 清理控制字符（statement/boundary 可能含换行符导致 JSON 解析失败）
    for k in ('statement', 'boundary', 'context'):
        if d.get(k) and isinstance(d[k], str):
            d[k] = d[k].replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    return d


CLAIMS_COLUMNS = 'id, statement, boundary, source_id, source_title, characteristics, confidence, extraction_level, status, opposing, possible_relations, arbitration, created, updated'


def action_arbitration(conn, status=None, limit=50):
    """仲裁视图：列出所有 opposing 断言对，标注仲裁状态。
    status: all / pending（未仲裁）/ decided（已仲裁），默认 pending。
    """
    cursor = conn.execute("PRAGMA table_info(claims)")
    cols = {row[1] for row in cursor.fetchall()}
    has_arbitration = 'arbitration' in cols

    rows = conn.execute("""
        SELECT id, statement, status, opposing, arbitration FROM claims
        WHERE opposing IS NOT NULL AND opposing != '' AND opposing != '[]'
        ORDER BY created DESC
    """).fetchall()

    pairs = []
    seen = set()
    for r in rows:
        cid = r['id']
        try:
            opp_list = json.loads(r['opposing']) if r['opposing'] else []
        except (json.JSONDecodeError, TypeError):
            opp_list = []
        for target in opp_list:
            key = tuple(sorted([cid, target]))
            if key in seen:
                continue
            seen.add(key)
            # 检查是否已仲裁（任一方 arbitration 记录含 target 即视为已仲裁）
            decided = False
            arb_info = None
            if has_arbitration and r['arbitration']:
                try:
                    arb_list = json.loads(r['arbitration']) if isinstance(r['arbitration'], str) else (r['arbitration'] or [])
                    for a in arb_list:
                        if a.get('target') == target:
                            decided = True
                            arb_info = a
                            break
                except (json.JSONDecodeError, TypeError):
                    pass
            pair_status = 'pending'
            if decided:
                pair_status = 'decided'
            elif status == 'decided':
                continue
            if status == 'pending' and decided:
                continue
            pair = {
                'claim_a': cid,
                'claim_b': target,
                'a_statement': (r['statement'] or '')[:80],
                'a_status': r['status'],
                'pair_status': pair_status,
                'arbitration': arb_info
            }
            pairs.append(pair)

    if status and status != 'all':
        pass  # 已在上方过滤
    return pairs[:limit]


# ============================================================
# LIKE 检索
# ============================================================

def action_search(conn, query, limit=20):
    """全文检索：claim_id精确查询 / FTS5 MATCH / LIKE fallback"""
    # claim_id 精确查询（CL开头的查询直接走WHERE id=?，不走FTS5）
    query_stripped = query.strip()
    if query_stripped.upper().startswith('CL') and query_stripped[2:].isdigit():
        rows = conn.execute(f"""
            SELECT {CLAIMS_COLUMNS} FROM claims WHERE id = ?
        """, (query_stripped.upper(),)).fetchall()
        return [fmt_row(r) for r in rows]

    # FTS5 MATCH
    try:
        rows = conn.execute("""
            SELECT c.id, c.statement, c.boundary, c.source_id, c.source_title,
                   c.characteristics, c.confidence, c.extraction_level, c.status,
                   c.opposing, c.possible_relations, c.created, c.updated
            FROM claims_fts f
            JOIN claims c ON f.claim_id = c.id
            WHERE claims_fts MATCH ?
            ORDER BY CASE c.status WHEN 'active' THEN 0 WHEN 'contested' THEN 1 ELSE 2 END, c.created DESC
            LIMIT ?
        """, (query, limit)).fetchall()
        if rows:
            return [fmt_row(r) for r in rows]
    except sqlite3.OperationalError:
        pass

    # fallback: LIKE 整句子串匹配
    like_pattern = f"%{query}%"
    rows = conn.execute(f"""
        SELECT {CLAIMS_COLUMNS} FROM claims
        WHERE statement LIKE ? OR boundary LIKE ? OR characteristics LIKE ?
        ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'contested' THEN 1 ELSE 2 END, created DESC
        LIMIT ?
    """, (like_pattern, like_pattern, like_pattern, limit)).fetchall()
    return [fmt_row(r) for r in rows]


def build_fts_query(query):
    """构造 FTS5 查询：整词 OR 连接。
    不过滤短词：unicode61 能处理2字中文词（逐字分词）；trigram 若对<3字报错由 action_hybrid 的 try/except fallback LIKE。
    实测发现 db 的 claims_fts 用 unicode61（非 trigram），2字中文词（流派/范式/海马）可正常匹配。"""
    query = query.strip()
    if not query:
        return query
    parts = query.split()
    if not parts:
        return query
    return ' OR '.join(parts)


def action_status(conn, status, limit=20):
    rows = conn.execute(f"""
        SELECT {CLAIMS_COLUMNS} FROM claims WHERE status = ?
        ORDER BY created DESC LIMIT ?
    """, (status, limit)).fetchall()
    return [fmt_row(r) for r in rows]


def action_source(conn, source_id, limit=50):
    rows = conn.execute(f"""
        SELECT {CLAIMS_COLUMNS} FROM claims WHERE source_id = ?
        ORDER BY created DESC LIMIT ?
    """, (source_id, limit)).fetchall()
    return [fmt_row(r) for r in rows]


def action_concept(conn, concept, limit=30):
    concept_row = conn.execute("SELECT claim_ids FROM concepts WHERE concept = ?", (concept,)).fetchone()

    if concept_row and concept_row['claim_ids']:
        claim_ids = json.loads(concept_row['claim_ids'])
        if claim_ids:
            placeholders = ','.join('?' * len(claim_ids))
            rows = conn.execute(f"""
                SELECT {CLAIMS_COLUMNS} FROM claims
                WHERE id IN ({placeholders})
                ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'contested' THEN 1 ELSE 2 END, created DESC
                LIMIT ?
            """, claim_ids + [limit]).fetchall()
            return [fmt_row(r) for r in rows]

    # aliases 模糊匹配（容错：旧库可能无 aliases 列）
    try:
        cur = conn.execute("PRAGMA table_info(concepts)")
        concept_cols = {row[1] for row in cur.fetchall()}
        if 'aliases' in concept_cols:
            alias_rows = conn.execute("SELECT claim_ids FROM concepts WHERE aliases LIKE ?", (f'%{concept}%',)).fetchall()
            all_ids = []
            for ar in alias_rows:
                try:
                    ids = json.loads(ar['claim_ids']) if ar['claim_ids'] else []
                    all_ids.extend(ids)
                except (json.JSONDecodeError, TypeError):
                    pass
            if all_ids:
                seen = set()
                unique_ids = [cid for cid in all_ids if not (cid in seen or seen.add(cid))]
                placeholders = ','.join('?' * len(unique_ids))
                rows = conn.execute(f"""
                    SELECT {CLAIMS_COLUMNS} FROM claims
                    WHERE id IN ({placeholders})
                    ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'contested' THEN 1 ELSE 2 END, created DESC
                    LIMIT ?
                """, unique_ids + [limit]).fetchall()
                if rows:
                    return [fmt_row(r) for r in rows]
    except sqlite3.Error:
        pass

    # fallback: characteristics LIKE
    like_pattern = f"%{concept}%"
    rows = conn.execute(f"""
        SELECT {CLAIMS_COLUMNS} FROM claims WHERE characteristics LIKE ?
        ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'contested' THEN 1 ELSE 2 END, created DESC
        LIMIT ?
    """, (like_pattern, limit)).fetchall()
    return [fmt_row(r) for r in rows]


def action_relations(conn, claim_id, strength='strong', exclude_types=None, limit=20):
    # 容错：检测 strength 列（旧库可能无）
    rel_cursor = conn.execute("PRAGMA table_info(relations)")
    rel_cols = {row[1] for row in rel_cursor.fetchall()}
    has_strength = 'strength' in rel_cols

    sql = """
        SELECT r.claim_a, r.claim_b, r.relation_type, r.context""" + (", r.strength" if has_strength else "") + """,
               c1.statement AS a_statement, c1.source_id AS a_source,
               c2.statement AS b_statement, c2.source_id AS b_source
        FROM relations r
        JOIN claims c1 ON r.claim_a = c1.id
        JOIN claims c2 ON r.claim_b = c2.id
        WHERE (r.claim_a = ? OR r.claim_b = ?)
    """
    params = [claim_id, claim_id]
    if strength != 'all' and has_strength:
        sql += " AND r.strength = ?"
        params.append(strength)
    if exclude_types:
        types = [t.strip() for t in exclude_types.split(',') if t.strip()]
        if types:
            placeholders = ','.join('?' * len(types))
            sql += f" AND r.relation_type NOT IN ({placeholders})"
            params.extend(types)
    if has_strength:
        sql += " ORDER BY CASE r.strength WHEN 'strong' THEN 0 ELSE 1 END, r.relation_type LIMIT ?"
    else:
        sql += " ORDER BY r.relation_type LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [fmt_row(r) for r in rows]


def action_summary(conn):
    stats = {
        "total_sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
        "total_claims": conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0],
        "active_claims": conn.execute("SELECT COUNT(*) FROM claims WHERE status='active'").fetchone()[0],
        "contested_claims": conn.execute("SELECT COUNT(*) FROM claims WHERE status='contested'").fetchone()[0],
        "merged_claims": conn.execute("SELECT COUNT(*) FROM claims WHERE status='merged'").fetchone()[0],
        "irrelevant_claims": conn.execute("SELECT COUNT(*) FROM claims WHERE status='irrelevant'").fetchone()[0],
        "total_concepts": conn.execute("SELECT COUNT(*) FROM concepts").fetchone()[0],
        "total_relations": conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0],
    }

    cursor = conn.execute("PRAGMA table_info(claims)")
    cols = {row[1] for row in cursor.fetchall()}
    if 'embedding' in cols:
        emb_count = conn.execute("SELECT COUNT(*) FROM claims WHERE embedding IS NOT NULL AND embedding != ''").fetchone()[0]
        stats["embedding_count"] = emb_count
        stats["embedding_coverage"] = f"{emb_count}/{stats['total_claims']}"
    else:
        stats["embedding_count"] = 0
        stats["embedding_coverage"] = "0% (列不存在)"

    # relations 统计（容错：旧库可能无 strength 列）
    rel_cursor = conn.execute("PRAGMA table_info(relations)")
    rel_cols = {row[1] for row in rel_cursor.fetchall()}
    if 'strength' in rel_cols:
        rel_rows = conn.execute("SELECT relation_type, strength, COUNT(*) as cnt FROM relations GROUP BY relation_type, strength").fetchall()
        stats["relations_detail"] = [{"relation_type": r[0], "strength": r[1], "count": r[2]} for r in rel_rows]
    else:
        rel_rows = conn.execute("SELECT relation_type, COUNT(*) as cnt FROM relations GROUP BY relation_type").fetchall()
        stats["relations_detail"] = [{"relation_type": r[0], "strength": "unknown(旧库无strength列)", "count": r[1]} for r in rel_rows]

    if 'opposing' in cols:
        opp_count = conn.execute("SELECT COUNT(*) FROM claims WHERE opposing IS NOT NULL AND opposing != '' AND opposing != '[]'").fetchone()[0]
        stats["opposing_count"] = opp_count
    else:
        stats["opposing_count"] = "N/A (旧库无opposing列)"

    # boundary 覆盖率统计
    if 'boundary' in cols:
        boundary_count = conn.execute("SELECT COUNT(*) FROM claims WHERE boundary IS NOT NULL AND boundary != ''").fetchone()[0]
        stats["boundary_count"] = boundary_count
        stats["boundary_coverage"] = f"{boundary_count}/{stats['total_claims']}"
    else:
        stats["boundary_count"] = "N/A"
        stats["boundary_coverage"] = "N/A (旧库无boundary列)"

    # leads 统计（leads表=待验证方向 + source_leads表=采集线索）
    try:
        stats["leads_open"] = conn.execute("SELECT COUNT(*) FROM leads WHERE status='open'").fetchone()[0]
        stats["leads_total"] = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    except sqlite3.Error:
        stats["leads_open"] = "N/A"
        stats["leads_total"] = "N/A"
    try:
        stats["source_leads_pending"] = conn.execute("SELECT COUNT(*) FROM source_leads WHERE status='pending'").fetchone()[0]
        stats["source_leads_total"] = conn.execute("SELECT COUNT(*) FROM source_leads").fetchone()[0]
    except sqlite3.Error:
        stats["source_leads_pending"] = "N/A"
        stats["source_leads_total"] = "N/A"

    return stats


def action_health(conn, project_path):
    """知识包健康诊断：孤儿/孤证/无边界/悬挂关系/leads积压/embedding缺口/contested/同源孤岛/jsonl一致性"""
    cursor = conn.execute("PRAGMA table_info(claims)")
    cols = {row[1] for row in cursor.fetchall()}
    has_boundary = 'boundary' in cols
    has_source_id = 'source_id' in cols
    has_confidence = 'confidence' in cols
    health = {}

    # 1. 孤儿断言：active 且无任何关系
    orphan_ids = conn.execute("SELECT c.id FROM claims c WHERE c.status='active' AND NOT EXISTS (SELECT 1 FROM relations r WHERE r.claim_a=c.id OR r.claim_b=c.id) LIMIT 10").fetchall()
    orphan_count = conn.execute("SELECT COUNT(*) FROM claims c WHERE c.status='active' AND NOT EXISTS (SELECT 1 FROM relations r WHERE r.claim_a=c.id OR r.claim_b=c.id)").fetchone()[0]
    health["orphan_claims"] = {"count": orphan_count, "samples": [r[0] for r in orphan_ids]}

    # 2. 孤证断言：confidence>=0.7 且来源只有1条支撑
    if has_source_id and has_confidence:
        lone = conn.execute("SELECT c.id FROM claims c WHERE c.status='active' AND CAST(c.confidence AS REAL)>=0.7 AND c.source_id IN (SELECT source_id FROM claims WHERE source_id IS NOT NULL AND source_id!='' GROUP BY source_id HAVING COUNT(*)=1) LIMIT 10").fetchall()
        lone_count = conn.execute("SELECT COUNT(*) FROM claims c WHERE c.status='active' AND CAST(c.confidence AS REAL)>=0.7 AND c.source_id IN (SELECT source_id FROM claims WHERE source_id IS NOT NULL AND source_id!='' GROUP BY source_id HAVING COUNT(*)=1)").fetchone()[0]
        health["lone_source_claims"] = {"count": lone_count, "samples": [r[0] for r in lone]}

    # 3. 无边界观点：active 且 boundary 为空
    if has_boundary:
        nobnd = conn.execute("SELECT id FROM claims WHERE status='active' AND (boundary IS NULL OR boundary='') LIMIT 10").fetchall()
        nobnd_count = conn.execute("SELECT COUNT(*) FROM claims WHERE status='active' AND (boundary IS NULL OR boundary='')").fetchone()[0]
        health["no_boundary_claims"] = {"count": nobnd_count, "samples": [r[0] for r in nobnd]}

    # 4. 悬挂关系：指向 merged/irrelevant
    dangling = conn.execute("SELECT r.claim_a, r.claim_b FROM relations r JOIN claims c1 ON r.claim_a=c1.id JOIN claims c2 ON r.claim_b=c2.id WHERE c1.status IN ('merged','irrelevant') OR c2.status IN ('merged','irrelevant') LIMIT 10").fetchall()
    health["dangling_relations"] = {"count": len(dangling), "samples": [{"a": r[0], "b": r[1]} for r in dangling]}

    # 5. leads 积压（leads表 + source_leads表）
    try:
        leads_open = conn.execute("SELECT COUNT(*) FROM leads WHERE status='open'").fetchone()[0]
        leads_old = conn.execute("SELECT target, created FROM leads WHERE status='open' ORDER BY created LIMIT 1").fetchone()
    except sqlite3.Error:
        leads_open = 0; leads_old = None
    try:
        sl_pending = conn.execute("SELECT COUNT(*) FROM source_leads WHERE status='pending'").fetchone()[0]
        sl_old = conn.execute("SELECT target, created FROM source_leads WHERE status='pending' ORDER BY created LIMIT 1").fetchone()
    except sqlite3.Error:
        sl_pending = 0; sl_old = None
    health["leads_backlog"] = {
        "leads_open": leads_open,
        "source_leads_pending": sl_pending,
        "total_pending": leads_open + sl_pending,
        "oldest_lead": {"target": leads_old[0], "created": leads_old[1]} if leads_old else None,
        "oldest_source_lead": {"target": sl_old[0], "created": sl_old[1]} if sl_old else None
    }

    # 6. embedding 缺口
    if 'embedding' in cols:
        emb_total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        emb_count = conn.execute("SELECT COUNT(*) FROM claims WHERE embedding IS NOT NULL AND embedding!=''").fetchone()[0]
        health["embedding_gap"] = {"coverage": f"{emb_count}/{emb_total}", "missing": emb_total - emb_count}

    # 7. contested 未仲裁
    health["contested"] = {"count": conn.execute("SELECT COUNT(*) FROM claims WHERE status='contested'").fetchone()[0]}

    # 7.1 未仲裁 opposing（P0-A）：opposing 字段非空但无 arbitration 记录的对
    if 'arbitration' in cols:
        opp_rows = conn.execute("SELECT id, opposing, arbitration FROM claims WHERE opposing IS NOT NULL AND opposing != '' AND opposing != '[]'").fetchall()
        pending_pairs = set()
        decided_pairs = set()
        for r in opp_rows:
            try:
                opp_list = json.loads(r['opposing']) if r['opposing'] else []
            except (json.JSONDecodeError, TypeError):
                opp_list = []
            arb_list = []
            try:
                arb_list = json.loads(r['arbitration']) if r['arbitration'] else []
            except (json.JSONDecodeError, TypeError):
                pass
            decided_targets = {a.get('target') for a in arb_list if isinstance(a, dict)}
            for target in opp_list:
                key = tuple(sorted([r['id'], target]))
                if target in decided_targets:
                    decided_pairs.add(key)
                else:
                    pending_pairs.add(key)
        health["unarbitrated_opposing"] = {"pair_count": len(pending_pairs), "pairs": sorted(pending_pairs)[:20]}
        health["arbitrated_opposing"] = {"pair_count": len(decided_pairs)}

    # 7.2 置信度-来源类型一致性（P1-C）：弱来源高置信度审计
    if has_source_id and has_confidence:
        try:
            weak_high = conn.execute("""
                SELECT c.id, c.source_id, c.confidence FROM claims c
                JOIN sources s ON c.source_id = s.id
                WHERE s.source_type IN ('web','expert','none','') AND CAST(c.confidence AS REAL) >= 0.8
                LIMIT 10
            """).fetchall()
            weak_high_count = conn.execute("""
                SELECT COUNT(*) FROM claims c
                JOIN sources s ON c.source_id = s.id
                WHERE s.source_type IN ('web','expert','none','') AND CAST(c.confidence AS REAL) >= 0.8
            """).fetchone()[0]
            health["weak_source_high_confidence"] = {"count": weak_high_count, "samples": [{"id": r[0], "source_id": r[1], "confidence": r[2]} for r in weak_high]}
        except sqlite3.Error:
            health["weak_source_high_confidence"] = {"error": "sources 表结构不兼容"}

    # 7.3 superseded 统计（P0-A）
    if 'status' in cols:
        try:
            health["superseded_claims"] = {"count": conn.execute("SELECT COUNT(*) FROM claims WHERE status='superseded'").fetchone()[0]}
        except sqlite3.Error:
            health["superseded_claims"] = {"count": 0}

    # 8. 同源孤岛
    if has_source_id:
        island = conn.execute("SELECT source_id FROM claims WHERE source_id IS NOT NULL AND source_id!='' GROUP BY source_id HAVING COUNT(*)=1 LIMIT 10").fetchall()
        island_count = conn.execute("SELECT COUNT(*) FROM (SELECT source_id FROM claims WHERE source_id IS NOT NULL AND source_id!='' GROUP BY source_id HAVING COUNT(*)=1)").fetchone()[0]
        health["single_claim_sources"] = {"count": island_count, "samples": [r[0] for r in island]}

    # 9. jsonl/sqlite 一致性
    jsonl_path = os.path.join(project_path, 'knowledge-pack', 'claims.jsonl')
    jsonl_count = 0
    if os.path.exists(jsonl_path):
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    jsonl_count += 1
    db_count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    health["jsonl_sqlite_consistency"] = {"jsonl_lines": jsonl_count, "db_claims": db_count, "match": jsonl_count == db_count}
    return health


def action_leads(conn, status='open', limit=20):
    """查待跟进线索（合并 leads 表=待验证方向 + source_leads 表=采集线索）"""
    results = []

    # 1. leads 表（待验证方向）
    try:
        rows = conn.execute("SELECT id, target, priority, reason, source_id, status, created FROM leads WHERE status=? ORDER BY created DESC LIMIT ?", (status, limit)).fetchall()
        for r in rows:
            d = fmt_row(r)
            d['source_table'] = 'leads（待验证方向）'
            results.append(d)
    except sqlite3.Error:
        pass

    # 2. source_leads 表（采集线索，status映射：open->pending）
    try:
        sl_status = 'pending' if status == 'open' else status
        rows = conn.execute("SELECT id, target, priority, context, source_article, status, created FROM source_leads WHERE status=? ORDER BY created DESC LIMIT ?", (sl_status, limit)).fetchall()
        for r in rows:
            d = fmt_row(r)
            d['source_table'] = 'source_leads（采集线索）'
            d['reason'] = d.pop('context', '')
            d['source_id'] = d.pop('source_article', '')
            results.append(d)
    except sqlite3.Error:
        pass

    return results[:limit]


# ============================================================
# 向量语义检索
# ============================================================

def call_embed_api(texts, base_url, api_key, model):
    url = f"{base_url}/embeddings"
    payload = json.dumps({"model": model, "input": texts}).encode('utf-8')
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        embeddings = sorted(result['data'], key=lambda x: x['index'])
        return [e['embedding'] for e in embeddings]


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def check_embedding_support(conn):
    cursor = conn.execute("PRAGMA table_info(claims)")
    cols = {row[1] for row in cursor.fetchall()}
    if 'embedding' not in cols:
        return False
    count = conn.execute("SELECT COUNT(*) FROM claims WHERE embedding IS NOT NULL AND embedding != ''").fetchone()[0]
    return count > 0


def action_vector(conn, query, base_url, api_key, model, limit=20, project_path=None):
    if not check_embedding_support(conn):
        return {"error": "无 embedding 数据，请先运行 embed-claims.py"}

    try:
        query_embeddings = call_embed_api([query], base_url, api_key, model)
        query_vec = query_embeddings[0]
    except Exception as e:
        return {"error": f"嵌入API调用失败: {str(e)[:200]}"}

    # 优先 numpy 矩阵化（带持久化缓存）
    if _HAS_NUMPY and project_path:
        matrix, ids = _load_embedding_matrix(conn, project_path)
        if matrix is not None and ids:
            qv = _np.array(query_vec, dtype=_np.float32)
            qn = _np.linalg.norm(qv)
            if qn == 0:
                return []
            sims = (matrix @ qv) / qn  # matrix 已归一化
            top_idx = _np.argsort(sims)[-limit:][::-1]
            results = []
            for i in top_idx:
                if sims[i] <= 0:
                    continue
                row = conn.execute(f"SELECT {CLAIMS_COLUMNS} FROM claims WHERE id = ?", (ids[i],)).fetchone()
                if row:
                    r = fmt_row(row)
                    r['vector_score'] = round(float(sims[i]), 4)
                    results.append(r)
            return results

    # 降级:纯Python循环(无numpy或矩阵构建失败)
    rows = conn.execute(f"""
        SELECT {CLAIMS_COLUMNS}, embedding FROM claims
        WHERE embedding IS NOT NULL AND embedding != ''
    """).fetchall()

    scored = []
    for row in rows:
        emb = json.loads(row['embedding'])
        sim = cosine_similarity(query_vec, emb)
        scored.append((sim, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for sim, row in scored[:limit]:
        r = fmt_row(row)
        r.pop('embedding', None)
        r['vector_score'] = round(sim, 4)
        results.append(r)

    return results


def action_hybrid(conn, query, base_url, api_key, model, limit=20, weights=None, project_path=None):
    like_scores = {}
    vec_scores = {}
    claim_cache = {}

    candidate_limit = limit * 3

    # FTS5 检索（优先），未命中或短词时 fallback LIKE
    fts_query = build_fts_query(query)
    fts_hit = False
    if fts_query:  # 空查询（全短词<3字）跳过 FTS5
        try:
            fts_rows = conn.execute("""
                SELECT claim_id, rank FROM claims_fts WHERE claims_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, candidate_limit)).fetchall()
            if fts_rows:
                fts_hit = True
                # FTS5 rank 是 bm25 相关性（负数，越小越相关），归一化到 0.5-1.0（命中区间）
                # 未命中的 like_score 保持 0.0，与命中最弱(0.5)有明确区分
                ranks = [r['rank'] for r in fts_rows]
                min_rank = min(ranks)
                max_rank = max(ranks)
                for r in fts_rows:
                    cid = r['claim_id']
                    if max_rank == min_rank:
                        like_scores[cid] = 1.0
                    else:
                        normalized = (max_rank - r['rank']) / (max_rank - min_rank)
                        like_scores[cid] = round(0.5 + 0.5 * normalized, 4)
                    if cid not in claim_cache:
                        row = conn.execute(f"SELECT {CLAIMS_COLUMNS} FROM claims WHERE id = ?", (cid,)).fetchone()
                        if row:
                            claim_cache[cid] = fmt_row(row)
        except sqlite3.OperationalError:
            pass
    # FTS5 未命中（0结果/空查询/报错）时 LIKE fallback
    if not fts_hit:
        like_pattern = f"%{query}%"
        try:
            like_rows = conn.execute(f"""
                SELECT {CLAIMS_COLUMNS} FROM claims
                WHERE statement LIKE ? OR boundary LIKE ? OR characteristics LIKE ?
                LIMIT ?
            """, (like_pattern, like_pattern, like_pattern, candidate_limit)).fetchall()
            if like_rows:
                for r in like_rows:
                    cid = r['id']
                    like_scores[cid] = 1.0
                    claim_cache[cid] = fmt_row(r)
        except Exception:
            pass

    # 向量检索（优先 numpy 矩阵化+持久化缓存；降级纯Python）
    if check_embedding_support(conn):
        try:
            query_embeddings = call_embed_api([query], base_url, api_key, model)
            query_vec = query_embeddings[0]

            used_numpy = False
            if _HAS_NUMPY and project_path:
                matrix, emb_ids = _load_embedding_matrix(conn, project_path)
                if matrix is not None and emb_ids:
                    qv = _np.array(query_vec, dtype=_np.float32)
                    qn = _np.linalg.norm(qv)
                    if qn > 0:
                        sims = (matrix @ qv) / qn  # matrix 已归一化
                        top_idx = _np.argsort(sims)[-candidate_limit:][::-1]
                        for i in top_idx:
                            if sims[i] <= 0:
                                continue
                            cid = emb_ids[i]
                            vec_scores[cid] = float(sims[i])
                            if cid not in claim_cache:
                                row = conn.execute(f"SELECT {CLAIMS_COLUMNS} FROM claims WHERE id = ?", (cid,)).fetchone()
                                if row:
                                    claim_cache[cid] = fmt_row(row)
                        used_numpy = True

            if not used_numpy:
                # 降级:纯Python循环
                rows = conn.execute(f"""
                    SELECT {CLAIMS_COLUMNS}, embedding FROM claims
                    WHERE embedding IS NOT NULL AND embedding != ''
                """).fetchall()
                scored = []
                for row in rows:
                    emb = json.loads(row['embedding'])
                    sim = cosine_similarity(query_vec, emb)
                    scored.append((sim, row))
                scored.sort(key=lambda x: x[0], reverse=True)
                for sim, row in scored[:candidate_limit]:
                    cid = row['id']
                    vec_scores[cid] = sim
                    if cid not in claim_cache:
                        r = fmt_row(row)
                        r.pop('embedding', None)
                        claim_cache[cid] = r
        except Exception:
            pass

    all_ids = set(like_scores.keys()) | set(vec_scores.keys())
    if not all_ids:
        return []

    if weights is None:
        weights = {'like': 0.4, 'vector': 0.6, 'auto_boost_short_query': True, 'short_query_threshold': 4}
    query_len = len(query.strip())
    if weights.get('auto_boost_short_query') and query_len <= weights.get('short_query_threshold', 4):
        LIKE_WEIGHT = 0.6  # 短查询(强术语)提升 like 权重，避免被泛词稀释
        VEC_WEIGHT = 0.4
    else:
        LIKE_WEIGHT = weights['like']
        VEC_WEIGHT = weights['vector']

    hybrid_results = []
    for cid in all_ids:
        like_s = like_scores.get(cid, 0.0)
        vec_s = vec_scores.get(cid, 0.0)
        hybrid_s = LIKE_WEIGHT * like_s + VEC_WEIGHT * vec_s
        row = claim_cache.get(cid, {})
        row['hybrid_score'] = round(hybrid_s, 4)
        row['like_score'] = round(like_s, 4)
        row['vector_score'] = round(vec_s, 4)
        hybrid_results.append(row)

    hybrid_results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
    return hybrid_results[:limit]


import re
_CONTROL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

def _clean_json(obj):
    """递归清理所有字符串值的控制字符，确保 JSON 输出可被 json.load 严格模式解析"""
    if isinstance(obj, str):
        return _CONTROL_RE.sub(' ', obj).replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ').replace('\t', ' ')
    elif isinstance(obj, dict):
        return {k: _clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_json(v) for v in obj]
    return obj


def main():
    parser = argparse.ArgumentParser(description='zhishibao 知识检索')
    parser.add_argument('--project-path', required=True, help='项目根目录路径')
    parser.add_argument('--action', required=True,
                        choices=['search', 'vector', 'hybrid', 'status', 'source', 'concept', 'relations', 'summary', 'health', 'leads', 'arbitration'],
                        help='检索模式')
    parser.add_argument('--query', help='search/vector/hybrid 的检索词')
    parser.add_argument('--status', help='status 模式的状态过滤；arbitration 模式的仲裁状态过滤(pending/decided/all)')
    parser.add_argument('--source-id', help='source 模式的来源ID')
    parser.add_argument('--concept', help='concept 模式的概念名')
    parser.add_argument('--claim-id', help='relations 模式的断言ID')
    parser.add_argument('--strength', choices=['strong', 'weak', 'all'], default='all', help='relations 模式的强度过滤（默认 all，配合 exclude-types 过滤噪声）')
    parser.add_argument('--exclude-types', default='same_source', help='relations 模式排除的关系类型，逗号分隔（默认 same_source 过滤同源噪声）')
    parser.add_argument('--limit', type=int, default=20, help='返回条数上限')
    args = parser.parse_args()

    conn = get_db_conn(args.project_path)
    base_url, api_key, model = load_embed_config(args.project_path)

    if args.action == 'search':
        if not args.query:
            print(json.dumps({"error": "search 需要 --query"}, ensure_ascii=False)); sys.exit(1)
        results = action_search(conn, args.query, args.limit)
    elif args.action == 'vector':
        if not args.query:
            print(json.dumps({"error": "vector 需要 --query"}, ensure_ascii=False)); sys.exit(1)
        results = action_vector(conn, args.query, base_url, api_key, model, args.limit, project_path=args.project_path)
    elif args.action == 'hybrid':
        if not args.query:
            print(json.dumps({"error": "hybrid 需要 --query"}, ensure_ascii=False)); sys.exit(1)
        weights = load_search_weights(args.project_path)
        results = action_hybrid(conn, args.query, base_url, api_key, model, args.limit, weights, project_path=args.project_path)
    elif args.action == 'status':
        if not args.status:
            print(json.dumps({"error": "status 需要 --status"}, ensure_ascii=False)); sys.exit(1)
        results = action_status(conn, args.status, args.limit)
    elif args.action == 'source':
        if not args.source_id:
            print(json.dumps({"error": "source 需要 --source-id"}, ensure_ascii=False)); sys.exit(1)
        results = action_source(conn, args.source_id, args.limit)
    elif args.action == 'concept':
        if not args.concept:
            print(json.dumps({"error": "concept 需要 --concept"}, ensure_ascii=False)); sys.exit(1)
        results = action_concept(conn, args.concept, args.limit)
    elif args.action == 'relations':
        if not args.claim_id:
            print(json.dumps({"error": "relations 需要 --claim-id"}, ensure_ascii=False)); sys.exit(1)
        results = action_relations(conn, args.claim_id, args.strength, args.exclude_types, args.limit)
    elif args.action == 'summary':
        results = action_summary(conn)
    elif args.action == 'health':
        results = action_health(conn, args.project_path)
    elif args.action == 'leads':
        results = action_leads(conn, args.status or 'open', args.limit)
    elif args.action == 'arbitration':
        results = action_arbitration(conn, args.status or 'pending', args.limit)

    output = {
        "action": args.action,
        "project_path": args.project_path,
        "count": len(results) if isinstance(results, list) else 1,
        "results": results,
    }
    print(json.dumps(_clean_json(output), ensure_ascii=False, indent=2))
    conn.close()


if __name__ == '__main__':
    main()
