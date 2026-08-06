#!/usr/bin/env python3
"""
zhishibao 按来源清除断言 - knowledge-purge-by-source.py
功能：按 source_id 删除该来源的所有断言 + 涉及这些断言的关系，用于知识管理员重建某 skill 的断言
使用：python knowledge-purge-by-source.py --project-path "..." --source-id "src:review:gorden-ppt-skill"
设计：claims.jsonl + relations.jsonl 是真相源，本脚本编辑 jsonl 后重建 SQLite 索引
流程：读 jsonl -> 找该 source 的断言 -> 删 claims + 涉及 relations -> 写回 -> 重建索引+关系+视图
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def read_jsonl(path):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def write_jsonl(path, items):
    with open(path, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def run_subprocess(script_name, project_path):
    script_path = os.path.join(get_script_dir(), script_name)
    try:
        result = subprocess.run(
            [sys.executable, script_path, '--project-path', project_path],
            capture_output=True, text=True, encoding='utf-8', timeout=300
        )
        return result.returncode == 0, result.stdout.strip()[-500:] if result.stdout else '', result.stderr.strip()[-500:] if result.stderr else ''
    except Exception as e:
        return False, '', str(e)[:200]


def purge_by_source(project_path, source_id):
    pack_dir = os.path.join(project_path, 'knowledge-pack')
    claims_path = os.path.join(pack_dir, 'claims.jsonl')
    relations_path = os.path.join(pack_dir, 'relations.jsonl')

    if not os.path.exists(claims_path):
        return {"error": f"claims.jsonl 不存在: {claims_path}"}

    claims = read_jsonl(claims_path)
    relations = read_jsonl(relations_path)

    # 找该 source_id 的断言 claim_id 集合
    purge_ids = set()
    kept_claims = []
    for claim in claims:
        cid = claim.get('claim_id') or claim.get('id', '')
        source = claim.get('source', {}) or {}
        if source.get('id', '') == source_id:
            purge_ids.add(cid)
        else:
            kept_claims.append(claim)

    if not purge_ids:
        return {
            "source_id": source_id,
            "purged_claims": 0,
            "purged_relations": 0,
            "note": "未找到该 source_id 的断言，无需清除"
        }

    # 删除涉及这些断言的关系（claim_a 或 claim_b 在 purge_ids 中）
    kept_relations = []
    purged_rel_count = 0
    for rel in relations:
        a = rel.get('claim_a', '')
        b = rel.get('claim_b', '')
        if a in purge_ids or b in purge_ids:
            purged_rel_count += 1
        else:
            kept_relations.append(rel)

    # 写回
    write_jsonl(claims_path, kept_claims)
    write_jsonl(relations_path, kept_relations)

    # 重建索引+关系+视图（embed 保留，不重跑）
    chain = {}
    ok, out, err = run_subprocess('knowledge-index-update.py', project_path)
    chain['index_update'] = 'ok' if ok else f'fail: {err}'

    ok, out, err = run_subprocess('build-relations.py', project_path)
    chain['build_relations'] = 'ok' if ok else f'fail: {err}'

    ok, out, err = run_subprocess('generate-knowledge-views.py', project_path)
    chain['generate_views'] = 'ok' if ok else f'fail: {err}'

    return {
        "source_id": source_id,
        "purged_claims": len(purge_ids),
        "purged_claim_ids": sorted(purge_ids),
        "purged_relations": purged_rel_count,
        "remaining_claims": len(kept_claims),
        "chain": chain
    }


def main():
    parser = argparse.ArgumentParser(description='zhishibao 按来源清除断言（重建用）')
    parser.add_argument('--project-path', required=True, help='项目根目录路径')
    parser.add_argument('--source-id', required=True, help='要清除的 source_id（如 src:review:gorden-ppt-skill）')
    parser.add_argument('--dry-run', action='store_true', help='只预览将删除的断言，不实际删除')
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    if not os.path.isdir(project_path):
        print(json.dumps({"error": f"路径不存在: {project_path}"}, ensure_ascii=False))
        sys.exit(1)

    if args.dry_run:
        pack_dir = os.path.join(project_path, 'knowledge-pack')
        claims_path = os.path.join(pack_dir, 'claims.jsonl')
        claims = read_jsonl(claims_path)
        preview = []
        for claim in claims:
            source = claim.get('source', {}) or {}
            if source.get('id', '') == args.source_id:
                cid = claim.get('claim_id') or claim.get('id', '')
                preview.append({"claim_id": cid, "statement": claim.get('statement', '')[:60]})
        print(json.dumps({"source_id": args.source_id, "would_purge": len(preview), "claims": preview}, ensure_ascii=False, indent=2))
        return

    result = purge_by_source(project_path, args.source_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
