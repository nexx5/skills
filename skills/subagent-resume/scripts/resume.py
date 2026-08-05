#!/usr/bin/env python3
"""按任务名称查询中断的 sub agent task_id，供 Task 工具接续。
父 agent 传入派发时的任务名称关键词，脚本全局匹配 session.title，返回 task_id + 中断状态 + parent 信息。
只读查询 opencode.db，不写入。"""
import sqlite3, json, sys, os, re, argparse


def get_db_path():
    home = os.path.expanduser("~")
    return os.path.join(home, ".local", "share", "opencode", "opencode.db")


def get_status(cur, cid, parent_id):
    """提取 sub agent session 的中断状态。"""
    cur.execute("SELECT count(*) FROM message WHERE session_id=?", (cid,))
    msg_count = cur.fetchone()[0]

    cur.execute(
        "SELECT json_extract(data,'$.finish') FROM message WHERE session_id=? AND json_extract(data,'$.role')='assistant' ORDER BY time_created DESC LIMIT 1",
        (cid,))
    r = cur.fetchone()
    finish = r[0] if r else None

    task_state = None
    task_result_empty = None
    if parent_id:
        cur.execute("SELECT data FROM part WHERE session_id=? AND data LIKE ?", (parent_id, f"%{cid}%"))
        for pr in cur.fetchall():
            d = pr[0].replace('\\"', '"')
            if f'<task id="{cid}"' in d:
                m = re.search(r'<task id="' + re.escape(cid) + r'" state="(\w+)">', d)
                if m:
                    task_state = m.group(1)
                m2 = re.search(r'<task_result>(.*?)</task_result>', d, re.DOTALL)
                task_result_empty = bool(m2 and m2.group(1).strip() == "")
                break

    if finish == "stop" and task_result_empty is False:
        interrupted = False
    elif finish in ("unknown", "error", "length", "content_filter", "tool_calls") or task_result_empty is True:
        interrupted = True
    else:
        interrupted = None

    return {
        "msg_count": msg_count,
        "last_finish": finish,
        "task_state": task_state,
        "task_result_empty": task_result_empty,
        "interrupted": interrupted,
    }


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="按任务名称查询中断 sub agent 的 task_id")
    ap.add_argument("--name", default=None, help="任务名称关键词（派发时写的描述），全局匹配 session.title")
    ap.add_argument("--session", default=None, help="指定父 session id，列其全部下级（排查用）")
    ap.add_argument("--db", default=None, help="opencode.db 路径（默认 ~/.local/share/opencode/opencode.db）")
    args = ap.parse_args()

    if not args.name and not args.session:
        print(json.dumps({"error": "需要 --name <任务名称> 或 --session <父session id>"}, ensure_ascii=False))
        sys.exit(1)

    db_path = args.db or get_db_path()
    if not os.path.exists(db_path):
        print(json.dumps({"error": f"数据库不存在: {db_path}", "hint": "运行 opencode db path 确认路径，或用 --db 指定"}, ensure_ascii=False))
        sys.exit(1)

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if args.name:
        cur.execute(
            "SELECT id,title,agent,parent_id,time_created,time_updated FROM session WHERE parent_id IS NOT NULL AND title LIKE ? ORDER BY time_created DESC",
            (f"%{args.name}%",))
    else:
        cur.execute(
            "SELECT id,title,agent,parent_id,time_created,time_updated FROM session WHERE parent_id=? ORDER BY time_created DESC",
            (args.session,))

    rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        q = {"name": args.name} if args.name else {"session": args.session}
        print(json.dumps({"query": q, "matches": [], "note": "无匹配的 sub agent"}, ensure_ascii=False, indent=2))
        conn.close()
        return

    matches = []
    for r in rows:
        cid = r["id"]
        pid = r["parent_id"]
        st = get_status(cur, cid, pid)
        parent_title = None
        if pid:
            cur.execute("SELECT title FROM session WHERE id=?", (pid,))
            pr = cur.fetchone()
            parent_title = pr[0] if pr else None
        matches.append({
            "task_id": cid,
            "title": r["title"],
            "agent": r["agent"],
            "parent_id": pid,
            "parent_title": parent_title,
            "time_created": r["time_created"],
            "time_updated": r["time_updated"],
            **st,
        })

    q = {"name": args.name} if args.name else {"session": args.session}
    print(json.dumps({"query": q, "matches": matches}, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == "__main__":
    main()
