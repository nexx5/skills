#!/usr/bin/env python3
"""
zhishibao 知识包初始化 - knowledge-db-init.py
功能：创建知识包 SQLite 索引层数据库
使用：python knowledge-db-init.py --project-path "<项目路径>"
设计：claims.jsonl 是真相源，SQLite 是影子索引，可从 jsonl 重建
"""

import sqlite3
import argparse
import os
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def get_schema_sql():
    """读取同目录下的 knowledge-schema.sql"""
    schema_path = Path(__file__).parent / 'knowledge-schema.sql'
    if not schema_path.exists():
        print(f"ERROR: schema 文件不存在: {schema_path}", file=sys.stderr)
        sys.exit(1)
    with open(schema_path, 'r', encoding='utf-8') as f:
        return f.read()


def init_database(db_path, schema_sql):
    """初始化数据库"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if os.path.exists(db_path):
        backup_path = db_path + ".bak"
        os.rename(db_path, backup_path)
        print(f"  已有数据库备份到: {backup_path}")

    conn = sqlite3.connect(db_path)
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    print(f"  数据库初始化完成: {db_path}")


def main():
    parser = argparse.ArgumentParser(description='zhishibao 知识包数据库初始化')
    parser.add_argument('--project-path', required=True, help='项目根目录路径（知识包在 <项目>/knowledge-pack/）')
    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    if not os.path.isdir(project_path):
        print(f"ERROR: 路径不存在: {project_path}", file=sys.stderr)
        sys.exit(1)

    db_path = os.path.join(project_path, 'knowledge-pack', 'index', 'knowledge.db')
    print(f"初始化知识包数据库: {db_path}")

    schema_sql = get_schema_sql()
    init_database(db_path, schema_sql)

    # 确保 claims.jsonl 存在
    jsonl_path = os.path.join(project_path, 'knowledge-pack', 'claims.jsonl')
    if not os.path.exists(jsonl_path):
        open(jsonl_path, 'w', encoding='utf-8').close()
        print(f"  创建空 claims.jsonl: {jsonl_path}")

    # 确保 relations.jsonl 存在
    rel_path = os.path.join(project_path, 'knowledge-pack', 'relations.jsonl')
    if not os.path.exists(rel_path):
        open(rel_path, 'w', encoding='utf-8').close()
        print(f"  创建空 relations.jsonl: {rel_path}")

    # 复制 config.json 模板（如果项目下没有）
    config_dest = os.path.join(project_path, 'knowledge-pack', 'config.json')
    if not os.path.exists(config_dest):
        config_src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
        if os.path.exists(config_src):
            import shutil
            shutil.copy2(config_src, config_dest)
            print(f"  复制 config.json 模板: {config_dest}")
            print(f"  请根据实际环境修改 config.json 中的嵌入模型配置")
        else:
            print(f"  ⚠️ 未找到 config.json 模板，请手动创建 {config_dest}")

    print("完成。")


if __name__ == '__main__':
    main()
