#!/usr/bin/env python3
"""
zhishibao 知识写入入口 - knowledge-ingest.py
功能：接收断言 JSON -> 校验 -> 写 claims.jsonl -> 触发索引+嵌入+关系+视图
使用：
    # 新增断言
    python knowledge-ingest.py --project-path "..." --claim '{"statement":"...","boundary":"..."}'
    # 批量
    python knowledge-ingest.py --project-path "..." --claims-file claims.json
    # AI 判断为 extend CL001
    python knowledge-ingest.py --project-path "..." --claim '{...}' --relation extends:CL001
    # AI 判断为 conflict CL001
    python knowledge-ingest.py --project-path "..." --claim '{...}' --relation opposing:CL001
    # AI 判断为 merge 进 CL001
    python knowledge-ingest.py --project-path "..." --claim '{...}' --merge-into CL001

融合纪律（AI 必须遵守）：
    ingest 前必须先 knowledge-search.py --action hybrid 检索候选，判断关系后再调本脚本。
    禁止不查直接 ingest。

文件锁：保护 claims.jsonl + relations.jsonl 的并发写入
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# ============================================================
# 文件锁
# ============================================================

def is_process_alive(pid):
    """Windows: 检查进程是否存活"""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def acquire_lock(lock_path, timeout=30):
    """获取文件锁，最多等待 timeout 秒"""
    pid = os.getpid()
    start = time.time()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(pid).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                with open(lock_path, 'r') as f:
                    old_pid = int(f.read().strip())
                if not is_process_alive(old_pid):
                    os.unlink(lock_path)
                    continue
            except (ValueError, IOError):
                pass
            if time.time() - start > timeout:
                return False
            time.sleep(1)


def release_lock(lock_path):
    try:
        os.unlink(lock_path)
    except OSError:
        pass


# ============================================================
# 输入校验
# ============================================================

FUZZY_WORDS = ['可能', '也许', '或许']


def validate_claim(claim, require_boundary=False):
    """校验断言，返回 (ok, error)"""
    statement = claim.get('statement', '').strip()
    if not statement:
        return False, "statement 不能为空"
    if len(statement) > 200:
        return False, f"statement 过长（{len(statement)} > 200）"

    if require_boundary:
        boundary = claim.get('boundary', '').strip()
        if not boundary:
            return False, "require-boundary 模式下 boundary 必填（事实断言必须有成立条件；无边界的是观点，不是知识）"

    confidence = claim.get('confidence', 0.5)
    try:
        confidence = float(confidence)
        if confidence < 0 or confidence > 1:
            return False, f"confidence 超出范围: {confidence}"
    except (ValueError, TypeError):
        return False, f"confidence 非数字: {confidence}"

    source = claim.get('source')
    if source:
        if not isinstance(source, dict):
            return False, "source 必须是对象"
        if not source.get('id') or not source.get('title'):
            return False, "source 有则必须包含 id 和 title"

    chars = claim.get('characteristics', [])
    if chars and len(chars) > 5:
        claim['characteristics'] = chars[:5]

    # 模糊词警告（不拒绝，但提示）
    for w in FUZZY_WORDS:
        if w in statement:
            return False, f"statement 含模糊词 '{w}'，请用 confidence 表达不确定性"

    return True, None


# ============================================================
# claim_id 分配
# ============================================================

def read_jsonl(path):
    """读取 jsonl 全部行"""
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
    """写回 jsonl 全部行（原子写入：先写 tmp 再 rename，防写一半崩溃损坏）"""
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)  # 原子 rename（同文件系统内）


def append_jsonl(path, item):
    """追加一行到 jsonl（写后 fsync 保证落盘）"""
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def next_claim_id(claims):
    """分配下一个 claim_id"""
    max_num = 0
    for c in claims:
        cid = c.get('claim_id') or c.get('id', '')
        if cid.startswith('CL'):
            try:
                num = int(cid[2:])
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
    return f"CL{max_num + 1:05d}"


# ============================================================
# 主流程
# ============================================================

def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def run_subprocess(script_name, project_path):
    """运行同目录下的脚本"""
    script_path = os.path.join(get_script_dir(), script_name)
    try:
        result = subprocess.run(
            [sys.executable, script_path, '--project-path', project_path],
            capture_output=True, text=True, encoding='utf-8', timeout=300
        )
        return result.returncode == 0, result.stdout.strip()[-500:] if result.stdout else '', result.stderr.strip()[-500:] if result.stderr else ''
    except Exception as e:
        return False, '', str(e)[:200]


def ingest(project_path, claims_data, relation=None, merge_into=None, status_override=None, require_boundary=False):
    """执行 ingest 流程"""
    pack_dir = os.path.join(project_path, 'knowledge-pack')
    claims_path = os.path.join(pack_dir, 'claims.jsonl')
    relations_path = os.path.join(pack_dir, 'relations.jsonl')
    lock_path = os.path.join(pack_dir, '.ingest.lock')

    # 确保文件存在
    os.makedirs(pack_dir, exist_ok=True)
    if not os.path.exists(claims_path):
        open(claims_path, 'w', encoding='utf-8').close()
    if not os.path.exists(relations_path):
        open(relations_path, 'w', encoding='utf-8').close()

    # 获取锁
    if not acquire_lock(lock_path, timeout=30):
        return {"error": "获取文件锁超时（另一进程正在写入），请重试"}

    try:
        existing_claims = read_jsonl(claims_path)
        existing_relations = read_jsonl(relations_path)

        # P0 安全校验：jsonl/SQLite 一致性检查
        # 防止 jsonl 被意外清空/损坏时 next_claim_id 从 CL00001 重新分配导致覆盖丢失
        try:
            import sqlite3
            for candidate in ['knowledge-pack/index', '2-执行/03-知识提炼', '03-知识提炼']:
                for db_name in ['knowledge.db', 'knowledge-index.db']:
                    db_path = os.path.join(project_path, candidate, db_name)
                    if os.path.exists(db_path):
                        _conn = sqlite3.connect(db_path)
                        db_count = _conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
                        _conn.close()
                        if db_count > 0 and len(existing_claims) == 0:
                            release_lock(lock_path)
                            return {"error": f"安全拦截：claims.jsonl 为空但 SQLite 有 {db_count} 条断言。jsonl 可能被损坏，请先从 SQLite 恢复 jsonl 再写入。", "db_claims": db_count, "jsonl_claims": 0}
                        if db_count > 0 and len(existing_claims) < db_count * 0.5:
                            release_lock(lock_path)
                            return {"error": f"安全拦截：claims.jsonl({len(existing_claims)}条)远少于 SQLite({db_count}条)。jsonl 可能不完整，请检查后再写入。", "db_claims": db_count, "jsonl_claims": len(existing_claims)}
                        break
                else:
                    continue
                break
        except Exception:
            pass  # SQLite 不存在或表不存在时跳过校验（新项目首次写入）

        now = datetime.now(timezone.utc).isoformat()

        results = []

        for claim in claims_data:
            ok, err = validate_claim(claim, require_boundary=require_boundary)
            if not ok:
                results.append({"error": err, "claim": claim})
                continue

            # --- merge-into 模式 ---
            if merge_into:
                new_id = next_claim_id(existing_claims)
                claim['claim_id'] = new_id
                claim['status'] = 'merged'
                claim['possible_relations'] = [f"merged_to:{merge_into}"]
                claim['created'] = now
                claim.setdefault('characteristics', [])
                claim.setdefault('confidence', 0.5)
                claim.setdefault('extraction_level', 'deep')
                claim.setdefault('opposing', [])
                existing_claims.append(claim)
                results.append({"action": "merged", "new_claim_id": new_id, "merged_to": merge_into})
                continue

            # --- 正常新增 ---
            new_id = next_claim_id(existing_claims)
            claim['claim_id'] = new_id
            claim['status'] = status_override or 'active'
            claim['created'] = now
            claim.setdefault('boundary', '')
            claim.setdefault('source', None)
            claim.setdefault('characteristics', [])
            claim.setdefault('confidence', 0.5)
            claim.setdefault('extraction_level', 'deep')
            claim.setdefault('opposing', [])
            claim.setdefault('possible_relations', [])

            # 处理 relation
            if relation:
                rel_type, target_id = relation.split(':', 1)
                # A8: rel_type 白名单校验
                REL_TYPE_WHITELIST = {'extends', 'coexist', 'opposing', 'alternative_to',
                                      'complements', 'similar_to', 'depends_on', 'supersedes', 'upstream_of'}
                if rel_type not in REL_TYPE_WHITELIST:
                    return {"error": f"非法 rel_type: {rel_type}, 白名单: {REL_TYPE_WHITELIST}"}
                # A8: target_id 存在性校验
                target_exists = any((c.get('claim_id') or c.get('id')) == target_id for c in existing_claims)
                if not target_exists:
                    return {"error": f"target_id {target_id} 不存在于 claims"}
                if rel_type == 'opposing':
                    # 双方标 contested + 互加 opposing
                    claim['status'] = status_override or 'contested'
                    claim['opposing'] = [target_id]
                    # 更新目标断言（在内存中）
                    for c in existing_claims:
                        if (c.get('claim_id') or c.get('id')) == target_id:
                            c['status'] = 'contested'
                            opp = c.get('opposing', [])
                            if new_id not in opp:
                                opp.append(new_id)
                            c['opposing'] = opp
                            break
                    # 记录 strong 关系
                    existing_relations.append({
                        'claim_a': new_id, 'claim_b': target_id,
                        'relation_type': 'opposing', 'strength': 'strong',
                        'context': 'AI 判断同边界矛盾', 'created': now
                    })
                else:  # extends, coexist, alternative_to, complements, similar_to, depends_on, supersedes
                    existing_relations.append({
                        'claim_a': new_id, 'claim_b': target_id,
                        'relation_type': rel_type, 'strength': 'strong',
                        'context': f'AI 判断 {rel_type}', 'created': now
                    })

            existing_claims.append(claim)
            results.append({
                "action": "ingested",
                "claim_id": new_id,
                "relation": relation,
                "status": claim['status']
            })

        # 循环外统一写回（避免重复写入）
        write_jsonl(claims_path, existing_claims)
        if relation or merge_into:
            write_jsonl(relations_path, existing_relations)

    finally:
        release_lock(lock_path)

    # --- 触发全链路 ---
    chain_results = {}
    ok, out, err = run_subprocess('knowledge-index-update.py', project_path)
    chain_results['index_update'] = 'ok' if ok else f'fail: {err}'

    ok, out, err = run_subprocess('embed-claims.py', project_path)
    chain_results['embed'] = 'ok' if ok else f'fail: {err}'

    ok, out, err = run_subprocess('build-relations.py', project_path)
    chain_results['relations'] = 'ok' if ok else f'fail: {err}'

    ok, out, err = run_subprocess('generate-knowledge-views.py', project_path)
    chain_results['views'] = 'ok' if ok else f'fail: {err}'

    return {"results": results, "chain": chain_results}


def write_lead(project_path, lead_data):
    """写入一条待跟进线索到 leads 表（自己连 db，ingest 主流程不直接连 db）"""
    from datetime import datetime, timezone
    import sqlite3
    conn = None
    for candidate in ['knowledge-pack/index', '2-执行/03-知识提炼', '03-知识提炼']:
        for db_name in ['knowledge.db', 'knowledge-index.db']:
            db_path = os.path.join(project_path, candidate, db_name)
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                break
        if conn:
            break
    if not conn:
        return {"error": "knowledge.db/knowledge-index.db 不存在"}
    conn.execute("""CREATE TABLE IF NOT EXISTS leads (
        id TEXT PRIMARY KEY, target TEXT NOT NULL, priority TEXT, reason TEXT,
        source_id TEXT, status TEXT DEFAULT 'open', created TEXT NOT NULL)""")
    existing = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    lead_id = f"LD{existing + 1:06d}"
    now = datetime.now(timezone.utc).isoformat()
    target = lead_data.get('target', '')
    if not target:
        conn.close()
        return {"error": "lead 必须有 target（可验证命题，非模糊方向）"}
    conn.execute("INSERT INTO leads (id, target, priority, reason, source_id, status, created) VALUES (?,?,?,?,?,?,?)",
        (lead_id, target, lead_data.get('priority'), lead_data.get('reason'),
         lead_data.get('source_id'), 'open', now))
    conn.commit()
    conn.close()
    return {"status": "success", "lead_id": lead_id, "target": target}


def write_arbitration(project_path, claim_a, claim_b, result, reason, decided_by='AI'):
    """
    仲裁一对 opposing 断言，写入仲裁结果到 claims.jsonl 真相源。
    result: supersede_a（A 取代 B，B 标 superseded）/
            supersede_b（B 取代 A，A 标 superseded）/
            coexist（双方保留，不同边界）/
            undetermined（无法裁决，双方保持 contested）
    规则：
      - supersede 时：被取代方 status -> superseded（保留可回溯），取胜方 status -> active，双方 arbitration 记录
      - coexist 时：双方 status -> active，arbitration 记录 result=coexist，opposing 关系保留但标记已仲裁
      - undetermined 时：双方保持 contested，arbitration 记录 result=undetermined（等待 L4 人类裁决）
    """
    pack_dir = os.path.join(project_path, 'knowledge-pack')
    claims_path = os.path.join(pack_dir, 'claims.jsonl')
    relations_path = os.path.join(pack_dir, 'relations.jsonl')
    lock_path = os.path.join(pack_dir, '.ingest.lock')

    if not os.path.exists(claims_path):
        return {"error": "claims.jsonl 不存在，无法仲裁"}
    if not acquire_lock(lock_path, timeout=30):
        return {"error": "获取文件锁超时"}

    try:
        existing_claims = read_jsonl(claims_path)
        existing_relations = read_jsonl(relations_path) if os.path.exists(relations_path) else []

        ca = next((c for c in existing_claims if (c.get('claim_id') or c.get('id')) == claim_a), None)
        cb = next((c for c in existing_claims if (c.get('claim_id') or c.get('id')) == claim_b), None)
        if not ca or not cb:
            return {"error": f"断言不存在: {claim_a}={bool(ca)}, {claim_b}={bool(cb)}"}

        now = datetime.now(timezone.utc).isoformat()
        arb_a = {"target": claim_b, "result": result, "decided_at": now, "decided_by": decided_by, "reason": reason}
        arb_b = {"target": claim_a, "result": result, "decided_at": now, "decided_by": decided_by, "reason": reason}

        def _add_arb(claim, arb):
            arr = claim.get('arbitration') or []
            if isinstance(arr, str):
                try:
                    arr = json.loads(arr)
                except json.JSONDecodeError:
                    arr = []
            # 同一对不重复记录
            arr = [x for x in arr if not (x.get('target') == arb['target'])]
            arr.append(arb)
            claim['arbitration'] = arr

        if result == 'supersede_a':
            # A 取胜，B 被取代
            _add_arb(ca, arb_a); _add_arb(cb, arb_b)
            ca['status'] = 'active'
            cb['status'] = 'superseded'
            # 关系：A supersedes B
            existing_relations = [r for r in existing_relations if not (r.get('claim_a') == claim_a and r.get('claim_b') == claim_b)]
            existing_relations.append({
                'claim_a': claim_a, 'claim_b': claim_b,
                'relation_type': 'supersedes', 'strength': 'strong',
                'context': f'仲裁: {reason}', 'created': now
            })
        elif result == 'supersede_b':
            _add_arb(ca, arb_a); _add_arb(cb, arb_b)
            ca['status'] = 'superseded'
            cb['status'] = 'active'
            existing_relations = [r for r in existing_relations if not (r.get('claim_a') == claim_a and r.get('claim_b') == claim_b)]
            existing_relations.append({
                'claim_a': claim_b, 'claim_b': claim_a,
                'relation_type': 'supersedes', 'strength': 'strong',
                'context': f'仲裁: {reason}', 'created': now
            })
        elif result == 'coexist':
            _add_arb(ca, arb_a); _add_arb(cb, arb_b)
            ca['status'] = 'active'
            cb['status'] = 'active'
        elif result == 'undetermined':
            _add_arb(ca, arb_a); _add_arb(cb, arb_b)
            ca['status'] = 'contested'
            cb['status'] = 'contested'
        else:
            return {"error": f"result 非法: {result}，应为 supersede_a / supersede_b / coexist / undetermined"}

        write_jsonl(claims_path, existing_claims)
        write_jsonl(relations_path, existing_relations)
    finally:
        release_lock(lock_path)

    # 触发索引更新（不重嵌入，保留 embedding）
    chain = {}
    ok, out, err = run_subprocess('knowledge-index-update.py', project_path)
    chain['index_update'] = 'ok' if ok else f'fail: {err}'
    ok, out, err = run_subprocess('build-relations.py', project_path)
    chain['relations'] = 'ok' if ok else f'fail: {err}'
    ok, out, err = run_subprocess('generate-knowledge-views.py', project_path)
    chain['views'] = 'ok' if ok else f'fail: {err}'

    return {"status": "success", "action": "arbitrate", "claim_a": claim_a, "claim_b": claim_b,
            "result": result, "chain": chain}


def main():
    parser = argparse.ArgumentParser(description='zhishibao 知识写入入口')
    parser.add_argument('--project-path', required=True, help='项目根目录路径')
    parser.add_argument('--claim', help='断言 JSON 字符串（单条）')
    parser.add_argument('--claims-file', help='断言 JSON 文件路径（数组，批量）')
    parser.add_argument('--relation', help='与已有断言的关系: extends:CL00001 / opposing:CL00001 / coexist:CL00001 / alternative_to:CL00001')
    parser.add_argument('--merge-into', help='合并到已有断言（语义重复时）: CL00001')
    parser.add_argument('--status', help='覆盖默认状态: active / contested / irrelevant')
    parser.add_argument('--lead', help='写入待跟进线索 JSON: {"target":"可验证命题","priority":"P1","reason":"...","source_id":"S0291"}')
    parser.add_argument('--arbitrate', nargs=2, metavar=('CLAIM_A', 'CLAIM_B'), help='仲裁一对 opposing 断言: CLAIM_A CLAIM_B')
    parser.add_argument('--arbitration-result', choices=['supersede_a', 'supersede_b', 'coexist', 'undetermined'],
                        help='仲裁结果: supersede_a(A胜) / supersede_b(B胜) / coexist(不同边界共存) / undetermined(无法裁决)')
    parser.add_argument('--arbitration-reason', help='仲裁理由（必填，作为仲裁记录与关系 context）')
    parser.add_argument('--arbitration-by', default='AI', help='仲裁方: AI / human')
    parser.add_argument('--require-boundary', action='store_true', help='强制 boundary 必填（事实断言入库时启用，无边界断言被拒绝）')
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    if not os.path.isdir(project_path):
        print(json.dumps({"error": f"路径不存在: {project_path}"}, ensure_ascii=False))
        sys.exit(1)

    # 仲裁分支（独立于 claim ingest）
    if args.arbitrate:
        if not args.arbitration_result:
            print(json.dumps({"error": "仲裁需要 --arbitration-result（supersede_a/supersede_b/coexist/undetermined）"}, ensure_ascii=False))
            sys.exit(1)
        if not args.arbitration_reason:
            print(json.dumps({"error": "仲裁需要 --arbitration-reason（理由必填）"}, ensure_ascii=False))
            sys.exit(1)
        result = write_arbitration(project_path, args.arbitrate[0].upper(), args.arbitrate[1].upper(),
                                   args.arbitration_result, args.arbitration_reason, args.arbitration_by)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # lead 写入分支（独立于 claim ingest）
    if args.lead:
        try:
            lead_data = json.loads(args.lead)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"lead JSON 解析失败: {e}"}, ensure_ascii=False))
            sys.exit(1)
        result = write_lead(project_path, lead_data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 解析输入
    claims_data = []
    if args.claim:
        try:
            claims_data = [json.loads(args.claim)]
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"claim JSON 解析失败: {e}"}, ensure_ascii=False))
            sys.exit(1)
    elif args.claims_file:
        try:
            with open(args.claims_file, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
                claims_data = data if isinstance(data, list) else [data]
        except (json.JSONDecodeError, IOError) as e:
            print(json.dumps({"error": f"claims-file 读取失败: {e}"}, ensure_ascii=False))
            sys.exit(1)
    else:
        print(json.dumps({"error": "需要 --claim 或 --claims-file"}, ensure_ascii=False))
        sys.exit(1)

    # 解析 relation
    relation = args.relation
    if relation:
        parts = relation.split(':', 1)
        if len(parts) != 2 or parts[0] not in ('extends', 'opposing', 'coexist', 'alternative_to'):
            print(json.dumps({"error": f"relation 格式错误: {relation}，应为 extends:CL00001 / opposing:CL00001 / coexist:CL00001 / alternative_to:CL00001"}, ensure_ascii=False))
            sys.exit(1)

    result = ingest(project_path, claims_data, relation=relation, merge_into=args.merge_into, status_override=args.status, require_boundary=args.require_boundary)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
