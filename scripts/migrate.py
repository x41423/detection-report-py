#!/usr/bin/env python3
"""Unified migration CLI for detection-report-py.

Usage:
    python scripts/migrate.py check    # Check migration status
    python scripts/migrate.py run      # Run all pending migrations
    python scripts/migrate.py verify   # Verify all migrations
    python scripts/migrate.py status   # Show detailed status
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.unified_migration import verify_all, run_all


def cmd_check():
    results = verify_all()
    all_done = True
    for stage, info in results.items():
        status = "OK" if info["completed"] else "--"
        if not info["completed"]:
            all_done = False
        print(f"  [{status}] {info['label']}")
    if all_done:
        print("所有迁移已完成")
    else:
        print("存在待执行的迁移，运行: python scripts/migrate.py run")


def cmd_run():
    print("开始执行统一迁移...")
    results = run_all()
    for stage, info in results.items():
        status = info["status"]
        symbol = "OK" if status in ("ok", "already_done") else "--"
        print(f"  [{symbol}] {info['label']}: {status}")
    failed = any(v["status"] == "failed" for v in results.values())
    if failed:
        print("部分迁移失败，请检查日志")
        sys.exit(1)
    else:
        print("全部迁移完成")


def cmd_verify():
    results = verify_all()
    all_done = all(v["completed"] for v in results.values())
    print(f"迁移验证: {'全部通过' if all_done else '存在未完成的迁移'}")
    for stage, info in results.items():
        status = "OK" if info["completed"] else "--"
        print(f"  [{status}] {info['label']}")


def cmd_status():
    results = verify_all()
    print("迁移状态:")
    for stage, info in results.items():
        status = "已完成" if info["completed"] else "未迁移"
        print(f"  {info['label']}: {status}")


def main():
    parser = argparse.ArgumentParser(description="统一数据迁移工具")
    parser.add_argument("command", choices=["check", "run", "verify", "status"],
                        help="迁移命令")
    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "run": cmd_run,
        "verify": cmd_verify,
        "status": cmd_status,
    }
    commands[args.command]()


if __name__ == "__main__":
    main()
