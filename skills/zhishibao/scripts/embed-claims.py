#!/usr/bin/env python3
"""
zhishibao 断言向量嵌入 - embed-claims.py
功能：对 claims 表中无 embedding 的断言生成向量嵌入
使用：
    python embed-claims.py --project-path "..."           # 增量嵌入
    python embed-claims.py --project-path "..." --full-rebuild  # 全量重建
嵌入内容：statement + boundary 拼接
配置优先级：config.json > 环境变量(EMBED_*/QMD_OPENAI_*) > 默认值
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


# ============================================================
# 配置读取：config.json > 环境变量 > 默认值
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


def get_db_conn(project_path):
    for candidate in ['knowledge-pack/index', '2-执行/03-知识提炼', '03-知识提炼']:
        for db_name in ['knowledge.db', 'knowledge-index.db']:
            db_path = os.path.join(project_path, candidate, db_name)
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                return conn
    print(f"ERROR: knowledge.db/knowledge-index.db 不存在 (project: {project_path})", file=sys.stderr)
    sys.exit(1)


def ensure_columns(conn):
    """检查并添加缺失的列"""
    cursor = conn.execute("PRAGMA table_info(claims)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    for col in ['embedding', 'embedding_model', 'embedding_at']:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE claims ADD COLUMN {col} TEXT")
            print(f"  已添加 claims.{col} 列")

    cursor = conn.execute("PRAGMA table_info(relations)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    if 'strength' not in existing_cols:
        conn.execute("ALTER TABLE relations ADD COLUMN strength TEXT DEFAULT 'strong'")
        print("  已添加 relations.strength 列")

    # concepts.aliases（同义词/译名，检索时模糊匹配）
    cursor = conn.execute("PRAGMA table_info(concepts)")
    concept_cols = {row[1] for row in cursor.fetchall()}
    if 'aliases' not in concept_cols:
        try:
            conn.execute("ALTER TABLE concepts ADD COLUMN aliases TEXT")
            print("  已添加 concepts.aliases 列")
        except sqlite3.Error:
            pass

    conn.commit()


BATCH_SIZE = 32
API_TIMEOUT = 120
MAX_RETRIES = 2


def call_embed_api(texts, base_url, api_key, model):
    """调用 OpenAI 兼容的 embeddings API"""
    url = f"{base_url}/embeddings"
    payload = json.dumps({"model": model, "input": texts}).encode('utf-8')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')

    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                embeddings = sorted(result['data'], key=lambda x: x['index'])
                return [e['embedding'] for e in embeddings]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')[:200]
            if attempt < MAX_RETRIES:
                print(f"  API HTTP {e.code}，重试 ({attempt+1}/{MAX_RETRIES})... {error_body}")
                continue
            raise RuntimeError(f"Embedding API HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES:
                print(f"  API连接失败，重试 ({attempt+1}/{MAX_RETRIES})... {e.reason}")
                continue
            raise RuntimeError(f"Embedding API连接失败: {e.reason}")
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"  API异常，重试 ({attempt+1}/{MAX_RETRIES})... {str(e)[:100]}")
                continue
            raise
    return []


def build_embed_text(row):
    """拼接断言文本用于嵌入"""
    parts = [row['statement'] or '']
    boundary = row['boundary'] or ''
    if boundary and boundary != '未明确':
        parts.append(boundary)
    return ' '.join(p for p in parts if p)


def embed_claims(conn, base_url, api_key, model, full_rebuild=False):
    now = datetime.now(timezone.utc).isoformat()

    if full_rebuild:
        print("全量重建：清除已有 embedding...")
        conn.execute("UPDATE claims SET embedding = NULL, embedding_model = NULL, embedding_at = NULL")
        conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    without_embed = conn.execute("SELECT COUNT(*) FROM claims WHERE embedding IS NULL OR embedding = ''").fetchone()[0]
    print(f"断言总数: {total}，待嵌入: {without_embed}，已嵌入: {total - without_embed}")

    if without_embed == 0:
        print("全部已嵌入，无需处理。")
        return

    offset = 0
    success_count = 0
    fail_count = 0

    while offset < without_embed:
        rows = conn.execute("""
            SELECT id, statement, boundary FROM claims
            WHERE embedding IS NULL OR embedding = ''
            ORDER BY id LIMIT ? OFFSET ?
        """, (BATCH_SIZE, offset)).fetchall()

        if not rows:
            break

        texts = [build_embed_text(row) for row in rows]
        claim_ids = [row['id'] for row in rows]

        valid_indices = [i for i, t in enumerate(texts) if t.strip()]
        if not valid_indices:
            offset += len(rows)
            continue

        valid_texts = [texts[i] for i in valid_indices]
        valid_ids = [claim_ids[i] for i in valid_indices]

        try:
            embeddings = call_embed_api(valid_texts, base_url, api_key, model)
        except RuntimeError as e:
            print(f"  批次嵌入失败 (offset={offset}): {e}")
            fail_count += len(valid_texts)
            offset += len(rows)
            continue

        if len(embeddings) != len(valid_texts):
            print(f"  警告: API返回{len(embeddings)}条，预期{len(valid_texts)}条，跳过本批")
            fail_count += len(valid_texts)
            offset += len(rows)
            continue

        for cid, emb in zip(valid_ids, embeddings):
            emb_json = json.dumps(emb, ensure_ascii=False)
            conn.execute(
                "UPDATE claims SET embedding = ?, embedding_model = ?, embedding_at = ? WHERE id = ?",
                (emb_json, model, now, cid)
            )
        conn.commit()

        success_count += len(valid_ids)
        if success_count % 100 == 0 or success_count == without_embed:
            print(f"  进度: {success_count}/{without_embed} ({success_count*100//without_embed}%)")

        offset += len(rows)

    print(f"\n完成: 成功 {success_count}，失败 {fail_count}")


def main():
    parser = argparse.ArgumentParser(description='zhishibao 断言向量嵌入')
    parser.add_argument('--project-path', required=True, help='项目根目录路径')
    parser.add_argument('--full-rebuild', action='store_true', help='全量重建')
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    if not os.path.isdir(project_path):
        print(f"ERROR: 路径不存在: {project_path}", file=sys.stderr)
        sys.exit(1)

    base_url, api_key, model = load_embed_config(project_path)
    print(f"项目: {project_path}")
    print(f"嵌入API: {base_url}/embeddings")
    print(f"嵌入模型: {model}")

    conn = get_db_conn(project_path)
    ensure_columns(conn)
    embed_claims(conn, base_url, api_key, model, full_rebuild=args.full_rebuild)

    total = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    embedded = conn.execute("SELECT COUNT(*) FROM claims WHERE embedding IS NOT NULL AND embedding != ''").fetchone()[0]
    coverage = f"{embedded*100//total}%" if total > 0 else "0%"
    print(f"\n嵌入覆盖率: {embedded}/{total} ({coverage})")

    conn.close()


if __name__ == '__main__':
    main()
