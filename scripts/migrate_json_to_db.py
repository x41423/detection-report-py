#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""迁移 JSON 数据到本地 SQLite 数据库的入口脚本（Phase 1 – 初步迁移）"""
import sys
import os

def main():
    # 将项目根加入路径，确保可以导入内部模块
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)

    try:
        from app.db.migration import migrate_json_to_db
        migrate_json_to_db()
        print("Migration completed (if no errors).")
    except Exception as e:
        print("Migration failed:", e)
        raise

if __name__ == "__main__":
    main()
