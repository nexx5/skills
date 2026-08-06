#!/usr/bin/env python3
"""
视图生成脚本：从SQLite索引层生成L0/L1视图文件。
L0-知识概貌.md：知识地图+概念反向索引+健康度（分析员必读入口）
L1视图：按主题/概念按需生成

新协议schema适配：
  claims: id, statement, boundary, source_id, source_title, characteristics,
          confidence(REAL), school, extraction_level, status, opposing,
          possible_relations, created, updated, embedding
  sources: id, title, source_type, url, raw_path, extract_path, analysis_path, created
  concepts: concept, claim_ids, source_ids

用法：
    python "<skill目录>/scripts/generate-knowledge-views.py" --project-path "..." --level L0
    python "<skill目录>/scripts/generate-knowledge-views.py" --project-path "..." --level L1 --topic "知识图谱"
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

# Windows PowerShell GBK编码修复：强制stdout用UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def validate_project_path(path: str) -> str:
    abs_path = os.path.abspath(path)
    if not os.path.isdir(abs_path):
        print(f"ERROR: 路径不存在: {abs_path}", file=sys.stderr)
        sys.exit(1)
    return abs_path


def get_db_path(project_path: str) -> str:
    for candidate in ['knowledge-pack/index', '2-执行/03-知识提炼', '03-知识提炼']:
        for db_name in ['knowledge.db', 'knowledge-index.db']:
            p = os.path.join(project_path, candidate, db_name)
            if os.path.exists(p):
                return p
    print(f"ERROR: 找不到 knowledge.db / knowledge-index.db", file=sys.stderr)
    sys.exit(1)


def get_db_conn(project_path: str) -> sqlite3.Connection:
    db_path = get_db_path(project_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def safe_query(conn, sql, args=(), default=None):
    """安全查询：表不存在时返回default"""
    try:
        return conn.execute(sql, args).fetchall()
    except sqlite3.Error:
        return default


def safe_count(conn, sql, default=0):
    """安全计数：表不存在时返回default"""
    try:
        return conn.execute(sql).fetchone()[0]
    except sqlite3.Error:
        return default


def truncate(text, max_len=40):
    if not text:
        return '未明确'
    return text[:max_len-3] + '...' if len(text) > max_len else text


def generate_l0(conn, project_path):
    """生成 L0-知识概貌.md（知识地图版）"""
    # schema 兼容检测：旧库用 subject/predicate/object，无 statement 列
    cursor = conn.execute("PRAGMA table_info(claims)")
    cols = {row[1] for row in cursor.fetchall()}
    if 'statement' not in cols:
        print("ERROR: 旧 schema 不兼容（claims 表无 statement 列，旧库用 subject/predicate/object）。该 db 需先迁移到新 schema 才能生成视图。", file=sys.stderr)
        sys.exit(1)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 统计
    total_sources = safe_count(conn, "SELECT COUNT(*) FROM sources")
    total_claims = safe_count(conn, "SELECT COUNT(*) FROM claims")
    active_claims = safe_count(conn, "SELECT COUNT(*) FROM claims WHERE status='active'")
    contested_claims = safe_count(conn, "SELECT COUNT(*) FROM claims WHERE status='contested'")
    merged_claims = safe_count(conn, "SELECT COUNT(*) FROM claims WHERE status='merged'")
    irrelevant_claims = safe_count(conn, "SELECT COUNT(*) FROM claims WHERE status='irrelevant'")
    total_concepts = safe_count(conn, "SELECT COUNT(*) FROM concepts")
    total_relations = safe_count(conn, "SELECT COUNT(*) FROM relations")

    # embedding覆盖
    emb_count = 0
    cursor = conn.execute("PRAGMA table_info(claims)")
    cols = {row[1] for row in cursor.fetchall()}
    has_embedding = 'embedding' in cols
    if has_embedding:
        emb_count = safe_count(conn, "SELECT COUNT(*) FROM claims WHERE embedding IS NOT NULL AND embedding != ''")

    # opposing
    opp_count = safe_count(conn, "SELECT COUNT(*) FROM claims WHERE opposing IS NOT NULL AND opposing != '' AND opposing != '[]'")

    # 获取项目名
    config_path = os.path.join(project_path, 'project.config.md')
    project_name = os.path.basename(project_path)
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        m = re.search(r'项目名[：:]\s*(.+?)$', content, re.MULTILINE)
        if m:
            project_name = m.group(1).strip()

    # 头部
    lines = [
        f"# 知识地图：{project_name}",
        f"",
        f"> 自动生成于 {now} | 来源 {total_sources} | 断言 {total_claims}（active {active_claims} / merged {merged_claims} / contested {contested_claims} / irrelevant {irrelevant_claims}）| 概念 {total_concepts} | 关系 {total_relations} | embedding {emb_count}/{total_claims}",
        f"> 分析员/报告员默认入口。先读这里定位，再用 knowledge-search.py 深入检索。",
        f"",
        f"---",
        f"",
    ]

    # ============================================================
    # 知识地图：按核心概念分区，每主题关键发现Top 5
    # ============================================================
    lines.append("## 知识地图（按核心概念分区，每主题关键发现Top 5）")
    lines.append("")
    lines.append("> 评分 = 关系数×1 + 争议性(opposing)×3。用 knowledge-search.py --action concept --concept 概念名 检索完整列表。")
    lines.append("")

    concept_rows = conn.execute(
        "SELECT concept, claim_ids FROM concepts "
        "WHERE claim_ids IS NOT NULL AND claim_ids != '' "
        "ORDER BY LENGTH(claim_ids) DESC LIMIT 15"
    ).fetchall()

    if concept_rows:
        for crow in concept_rows:
            concept = crow['concept']
            try:
                claim_ids = json.loads(crow['claim_ids'])
            except (json.JSONDecodeError, TypeError):
                continue
            if not claim_ids or len(claim_ids) < 2:
                continue

            placeholders = ','.join('?' * len(claim_ids))
            # 新协议：用 statement 显示，用 opposing/relations 评分
            claims = conn.execute(f"""
                SELECT c.id, c.statement, c.boundary, c.confidence, c.source_id,
                    (SELECT COUNT(*) FROM relations r WHERE r.claim_a = c.id OR r.claim_b = c.id) AS relation_count,
                    (CASE WHEN c.opposing IS NOT NULL AND c.opposing != '' AND c.opposing != '[]' THEN 1 ELSE 0 END) AS opposing_count
                FROM claims c
                WHERE c.id IN ({placeholders}) AND c.status = 'active'
                ORDER BY (relation_count + opposing_count * 3) DESC
                LIMIT 5
            """, claim_ids).fetchall()

            if not claims:
                continue

            lines.append(f"### {concept}（{len(claim_ids)}条断言）")
            lines.append("")
            lines.append("| 断言ID | 断言(statement) | 边界 | 置信度 | 来源 |")
            lines.append("|---|---|---|---|---|")
            for row in claims:
                statement = truncate(row['statement'], 60)
                b = row['boundary'] or ''
                boundary = ('⚑ ' + truncate(b, 60)) if b else truncate(b, 60)
                lines.append(f"| {row['id']} | {statement} | {boundary} | {row['confidence']} | {row['source_id'] or '-'} |")
            lines.append("")
    else:
        lines.append("（无概念索引）\n")

    # ============================================================
    # 全局枢纽断言（高关系度，跨概念）
    # ============================================================
    lines.append("## 全局枢纽断言（高关系度，跨概念）")
    lines.append("")
    lines.append("> 按 relation_count + opposing×3 全局排序 Top10，暴露不在概念分区 Top5 里的跨概念枢纽。⚑=有边界。")
    lines.append("")
    try:
        hub_rows = conn.execute("""
            SELECT c.id, c.statement, c.boundary, c.confidence, c.source_id,
                (SELECT COUNT(*) FROM relations r WHERE r.claim_a = c.id OR r.claim_b = c.id) AS rel_cnt,
                (CASE WHEN c.opposing IS NOT NULL AND c.opposing != '' AND c.opposing != '[]' THEN 1 ELSE 0 END) AS opp
            FROM claims c WHERE c.status='active'
            ORDER BY (rel_cnt + opp*3) DESC LIMIT 10
        """).fetchall()
        if hub_rows:
            lines.append("| 断言ID | 断言(statement) | 边界 | 置信度 | 来源 | 关系数 |")
            lines.append("|---|---|---|---|---|---|")
            for row in hub_rows:
                statement = truncate(row['statement'], 60)
                b = row['boundary'] or ''
                boundary = ('⚑ ' + truncate(b, 60)) if b else truncate(b, 60)
                lines.append(f"| {row['id']} | {statement} | {boundary} | {row['confidence']} | {row['source_id'] or '-'} | {row['rel_cnt']} |")
            lines.append("")
    except sqlite3.Error:
        lines.append("（查询失败）\n")

    # ============================================================
    # opposing 未仲裁
    # ============================================================
    if opp_count > 0:
        lines.append("## opposing 标记（未仲裁）")
        lines.append(f"> {opp_count} 条断言有对立标记，需逐条判断是同边界矛盾还是不同边界互补。")
        lines.append("")
        opp_rows = conn.execute("""
            SELECT id, statement, opposing FROM claims
            WHERE opposing IS NOT NULL AND opposing != '' AND opposing != '[]'
            LIMIT 20
        """).fetchall()
        if opp_rows:
            lines.append("| 断言ID | 断言(statement) | opposing |")
            lines.append("|---|---|---|")
            for row in opp_rows:
                statement = truncate(row['statement'], 50)
                opp = truncate(str(row['opposing']), 40)
                lines.append(f"| {row['id']} | {statement} | {opp} |")
            lines.append("")

    # ============================================================
    # 概念反向索引
    # ============================================================
    lines.append("## 概念反向索引（前20，含关联断言ID）")
    lines.append("")
    concept_rows = conn.execute(
        "SELECT concept, claim_ids, source_ids FROM concepts ORDER BY LENGTH(claim_ids) DESC LIMIT 20"
    ).fetchall()
    if concept_rows:
        lines.append("| 概念 | 断言数 | 来源数 | 关联断言ID（前5） |")
        lines.append("|---|---|---|---|")
        for row in concept_rows:
            claim_count = len(json.loads(row['claim_ids'])) if row['claim_ids'] else 0
            src_count = len(json.loads(row['source_ids'])) if row['source_ids'] else 0
            claim_ids = json.loads(row['claim_ids'])[:5] if row['claim_ids'] else []
            claim_str = ', '.join(claim_ids) if claim_ids else '-'
            lines.append(f"| {row['concept']} | {claim_count} | {src_count} | {claim_str} |")
        lines.append("")
    else:
        lines.append("（无概念索引）\n")

    # ============================================================
    # 关系统计
    # ============================================================
    if total_relations > 0:
        lines.append("## 关系统计")
        lines.append("")
        rel_rows = conn.execute(
            "SELECT relation_type, strength, COUNT(*) as cnt FROM relations GROUP BY relation_type, strength ORDER BY cnt DESC"
        ).fetchall()
        if rel_rows:
            lines.append("| 关系类型 | 强度 | 数量 |")
            lines.append("|---|---|---|")
            for row in rel_rows:
                lines.append(f"| {row['relation_type']} | {row['strength'] or 'strong'} | {row['cnt']} |")
            lines.append("")

    # ============================================================
    # 知识健康度
    # ============================================================
    lines.append("## 知识健康度")
    lines.append("")
    health = []
    if contested_claims > 0:
        health.append(f"⚠️ {contested_claims} 条 contested 断言待仲裁")
    if opp_count > 0:
        health.append(f"⚠️ {opp_count} 条 opposing 标记未仲裁")
    if active_claims == 0:
        health.append("⚠️ 无 active 断言")
    if total_sources == 0:
        health.append("⚠️ 无来源记录")
    if has_embedding and emb_count < total_claims * 0.9:
        health.append(f"⚠️ embedding 覆盖率低: {emb_count}/{total_claims}")
    if not health:
        health.append("✅ 知识一致性良好")
    for h in health:
        lines.append(f"- {h}")
    lines.append("")

    content = '\n'.join(lines)

    # 写入文件
    if os.path.isdir(os.path.join(project_path, 'knowledge-pack')):
        output_dir = os.path.join(project_path, 'knowledge-pack', 'views')
    else:
        output_dir = os.path.join(project_path, '2-执行', '03-知识提炼')
        if not os.path.isdir(output_dir):
            output_dir = os.path.join(project_path, '03-知识提炼')
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, 'L0-知识概貌.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return output_path


def generate_l1(conn, project_path, topic):
    """生成 L1 主题视图"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 新协议：用 statement/boundary/characteristics 匹配
    topic_pattern = f"%{topic}%"
    rows = conn.execute("""
        SELECT id, statement, boundary, source_id, source_title, characteristics,
               confidence, status, created
        FROM claims
        WHERE statement LIKE ? OR boundary LIKE ? OR characteristics LIKE ?
        ORDER BY CASE status
            WHEN 'active' THEN 0
            WHEN 'contested' THEN 1
            WHEN 'merged' THEN 2
            WHEN 'irrelevant' THEN 3
        END, created DESC
    """, (topic_pattern, topic_pattern, topic_pattern)).fetchall()

    lines = [
        f"# L1 主题视图：{topic}",
        f"",
        f"> 自动生成于 {now} | 关联断言 {len(rows)} 条",
        f">",
        f"> 这是按需生成的深入视图。如需更完整信息，请直接检索 SQLite。",
        f"",
        f"---",
        f"",
    ]

    if not rows:
        lines.append(f"未找到与「{topic}」相关的断言。")
        lines.append("")
        lines.append("建议：")
        lines.append(f"1. 用 `knowledge-search.py --action search --query \"{topic}\"` 做全文检索")
        lines.append("2. 用 `knowledge-search.py --action vector --query \"{topic}\"` 做语义检索")
        lines.append("3. 检查概念标签是否匹配")
        content = '\n'.join(lines)

        if os.path.isdir(os.path.join(project_path, 'knowledge-pack')):
            output_dir = os.path.join(project_path, 'knowledge-pack', 'views')
        else:
            output_dir = os.path.join(project_path, '2-执行', '03-知识提炼')
        os.makedirs(output_dir, exist_ok=True)
        safe_topic = topic.replace('/', '_').replace('\\', '_')
        output_path = os.path.join(output_dir, f'L1-{safe_topic}.md')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_path

    # 按状态分组
    active = [r for r in rows if r['status'] == 'active']
    contested = [r for r in rows if r['status'] == 'contested']
    merged = [r for r in rows if r['status'] == 'merged']

    def fmt_claims_table(claims, max_claims=80):
        if not claims:
            return "（暂无）\n"
        result = [
            "| 断言ID | 断言(statement) | 边界 | 置信度 | 来源 |",
            "|---|---|---|---|---|",
        ]
        for row in claims[:max_claims]:
            statement = truncate(row['statement'], 60)
            b = row['boundary'] or ''
            boundary = ('⚑ ' + truncate(b, 60)) if b else truncate(b, 60)
            result.append(f"| {row['id']} | {statement} | {boundary} | {row['confidence']} | {row['source_id'] or '-'} |")
        if len(claims) > max_claims:
            result.append(f"| ... | 共 {len(claims)} 条，仅显示前 {max_claims} 条 | | | |")
        return '\n'.join(result) + '\n'

    lines.append(f"## Active 断言（{len(active)} 条）")
    lines.append("")
    lines.append(fmt_claims_table(active, max_claims=80))

    if contested:
        lines.append(f"## Contested 断言（{len(contested)} 条）")
        lines.append("")
        lines.append(fmt_claims_table(contested, max_claims=20))

    if merged:
        lines.append(f"## Merged 断言（{len(merged)} 条，保留历史）")
        lines.append("")
        lines.append(fmt_claims_table(merged, max_claims=10))

    # 关联来源
    source_ids = set()
    for row in rows:
        if row['source_id']:
            source_ids.add(row['source_id'])

    if source_ids:
        placeholders = ','.join('?' * len(source_ids))
        src_rows = conn.execute(
            f"SELECT id, title, url FROM sources WHERE id IN ({placeholders})",
            list(source_ids)
        ).fetchall()

        if src_rows:
            lines.append("## 关联来源")
            lines.append("")
            lines.append("| 来源ID | 标题 | URL |")
            lines.append("|---|---|---|")
            for row in src_rows:
                title = truncate(row['title'], 50)
                lines.append(f"| {row['id']} | {title} | {row['url'] or '-'} |")
            lines.append("")

    content = '\n'.join(lines)

    # 写入文件
    if os.path.isdir(os.path.join(project_path, 'knowledge-pack')):
        output_dir = os.path.join(project_path, 'knowledge-pack', 'views')
    else:
        output_dir = os.path.join(project_path, '2-执行', '03-知识提炼')
        if not os.path.isdir(output_dir):
            output_dir = os.path.join(project_path, '03-知识提炼')
    os.makedirs(output_dir, exist_ok=True)

    safe_topic = topic.replace('/', '_').replace('\\', '_')
    output_path = os.path.join(output_dir, f'L1-{safe_topic}.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    return output_path


def main():
    parser = argparse.ArgumentParser(description='知识视图生成')
    parser.add_argument('--project-path', required=True, type=validate_project_path,
                        help='项目根目录路径')
    parser.add_argument('--level', choices=['L0', 'L1'], default='L0',
                        help='视图层级：L0=知识地图，L1=主题视图')
    parser.add_argument('--topic', help='L1视图的主题')
    args = parser.parse_args()

    conn = get_db_conn(args.project_path)

    if args.level == 'L0':
        output = generate_l0(conn, args.project_path)
        print(json.dumps({'status': 'success', 'level': 'L0', 'output': output}, ensure_ascii=False, indent=2))
    elif args.level == 'L1':
        if not args.topic:
            print("ERROR: L1 视图需要 --topic 参数", file=sys.stderr)
            sys.exit(1)
        output = generate_l1(conn, args.project_path, args.topic)
        print(json.dumps({'status': 'success', 'level': 'L1', 'topic': args.topic, 'output': output}, ensure_ascii=False, indent=2))

    conn.close()


if __name__ == '__main__':
    main()
