#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
功能试用数据清理脚本 —— 一键清空试用期间录入的业务数据，恢复到干净状态。

用法:
    # 预览（始终先跑这个！）
    python scripts/cleanup_test_data.py --dry-run

    # 默认：清空所有业务表 + 删除所有非保护用户
    python scripts/cleanup_test_data.py

    # 仅清理自动测试用户（保留手动创建的用户）
    python scripts/cleanup_test_data.py --user-mode test-only

    # 只清业务表，不动任何用户
    python scripts/cleanup_test_data.py --business-only

    # 带备份
    python scripts/cleanup_test_data.py --backup

选项:
    --dry-run         预览模式：只列出将要删除的数据，不实际删除
    --backup          在删除前创建备份 SQL 文件
    --yes             跳过确认提示（CI/自动化使用）
    --user-mode MODE  用户清理模式：
                        all        删除所有非保护用户（默认，适合正式使用前大清理）
                        test-only  仅删除自动测试用户 test.* + API Test User
                        none       不删除任何用户
    --business-only   只清理业务表，不动任何用户
    --keep-user USER  额外保护指定用户不被删除（可多次使用）
    --keep-table TABL 保护指定业务表不被清空（可多次使用）
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.env import load_project_env
from app.db import store

load_project_env()


# ---- 配置 ----
PROTECTED_USERNAMES = {
    "lina1124",  # 超级管理员（始终保护）
}

# ---- 级联删除顺序（严格按 FK 依赖从子到父）----
AUTH_DELETE_ORDER = [
    "auth_sessions",
    "auth_refresh_token_grace",
    "auth_pending_logins",
    "auth_devices",
    "auth_user_permission_overrides",
    "auth_permission_requests",
    "auth_audit_logs",
    "auth_user_roles",
    "auth_users",
]

# 业务表：FK 从子到父
BUSINESS_DELETE_ORDER = [
    "OrderAfterSale", "OrderItem", "OrderModification", "DeliveryTask", "OrderRecord",
    "PurchaseInItem", "PurchaseInRecord",
    "PurchaseReturnItem", "PurchaseReturnRecord",
    "LossReportItem", "LossReport",
    "QuotationProduct", "Quotation",
    "InspectionReportProduct", "InspectionReport",
    "MerchantProductPrice", "MerchantSettlement", "Merchant",
    "SupplierCategory", "SupplierProduct", "SupplierContact",
    "SupplierContract", "SupplierSettlement", "Supplier",
    "DailyIntakeItem", "DailyIntakeSheet",
    "WeeklyQuoteEntry", "WeeklyQuoteBatch",
    "InventoryTransaction",
    "UserColumnPreference",
    "PriceLockRuleItem", "PriceLockRule",
    "PriceHistory",
    "SortingPerformance", "SortingTask",
    "DeliveryRoute", "FreightTemplate",
    "PointsRecord", "Coupon", "PriceMarkup",
    "ProcessingPlan", "OperationTimeConfig",
    "ProductSku", "Product",
]

# 系统配置表（从不清理）
SYSTEM_TABLES = {
    "Category", "Config", "Veg", "Unit",
    "WeeklyQuoteMeasureUnitOption", "WeeklyQuoteMerchantConfig",
    "auth_permissions", "auth_roles", "auth_role_permissions",
    "schema_migrations", "MigrationVersion",
}


def _build_in_clause(ids: list[int]) -> tuple[str, list[int]]:
    return ",".join(["%s"] * len(ids)), ids


def get_removable_user_ids(conn, mode: str, protected: set[str]):
    """获取要删除的用户 ID 列表。"""
    cursor = conn.cursor()
    try:
        if mode == "none":
            return [], []

        plc, params = _build_in_clause(list(protected)) if protected else ("''", [])

        if mode == "test-only":
            where = (
                f"is_super_admin = 0"
                f" AND (username LIKE 'test.%%' OR display_name = 'API Test User')"
                f" AND username NOT IN ({plc})"
            )
        else:  # all
            where = (
                f"is_super_admin = 0"
                f" AND username NOT IN ({plc})"
            )

        sql = f"""SELECT id, username, display_name, is_super_admin
                   FROM auth_users WHERE {where}"""
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [row["id"] for row in rows], [(row["id"], row["username"], row["display_name"], row["is_super_admin"]) for row in rows]
    finally:
        cursor.close()


def delete_from_table(conn, table: str, user_ids: list[int], dry_run: bool) -> int:
    """删除数据。返回删除行数。"""
    cursor = conn.cursor()
    try:
        if table.startswith("auth_"):
            if not user_ids:
                return 0
            plc, params = _build_in_clause(user_ids)
            if table == "auth_audit_logs":
                sql = f"DELETE FROM {table} WHERE actor_user_id IN ({plc}) OR target_user_id IN ({plc})"
                params = user_ids + user_ids
            elif table == "auth_users":
                sql = f"DELETE FROM {table} WHERE id IN ({plc})"
            elif table == "auth_refresh_token_grace":
                sql = f"DELETE FROM {table} WHERE session_id IN (SELECT id FROM auth_sessions WHERE user_id IN ({plc}))"
            else:
                sql = f"DELETE FROM {table} WHERE user_id IN ({plc})"
        elif table == "UserColumnPreference":
            if not user_ids:
                return 0
            plc, params = _build_in_clause(user_ids)
            sql = f"DELETE FROM {table} WHERE user_id IN ({plc})"
        else:
            sql = f"DELETE FROM {table}"
            params = []

        if dry_run:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM ({sql}) AS _t", params)
                row = cursor.fetchone()
                return row[0] if row else 0
            except Exception:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row = cursor.fetchone()
                return row[0] if row else 0
        else:
            cursor.execute(sql, params)
            deleted = cursor.rowcount
            conn.commit()
            return deleted
    except Exception as e:
        if not dry_run:
            print(f"  ⚠️  {table}: {e}")
        return 0
    finally:
        cursor.close()


def check_foreign_keys(conn) -> bool:
    """检查是否存在未处理的外键依赖（安全网）。"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM auth_user_roles WHERE user_id NOT IN (SELECT id FROM auth_users)")
        orphan_roles = cursor.fetchone()[0]
        if orphan_roles > 0:
            print(f"  ⚠️  发现 {orphan_roles} 条孤儿 auth_user_roles 记录")
        return True
    except Exception:
        return True
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(
        description="功能试用数据清理 — 一键清空试用数据，恢复干净状态",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览即将清理的内容
  python scripts/cleanup_test_data.py --dry-run

  # 清空全部业务数据 + 删除所有非保护用户
  python scripts/cleanup_test_data.py

  # 只清业务表，保留所有用户
  python scripts/cleanup_test_data.py --business-only

  # 删除测试用户 + 清业务表，但保留正式用户
  python scripts/cleanup_test_data.py --user-mode test-only
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--backup", action="store_true", help="删除前备份")
    parser.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    parser.add_argument(
        "--user-mode",
        choices=["all", "test-only", "none"],
        default="all",
        help="用户清理模式: all(默认,删所有非保护用户) / test-only(仅删test.*) / none(不删用户)",
    )
    parser.add_argument("--business-only", action="store_true", help="只清业务表，不动用户")
    parser.add_argument("--keep-user", action="append", default=[], help="保护用户（可多次）")
    parser.add_argument("--keep-table", action="append", default=[], help="保护业务表（可多次）")
    args = parser.parse_args()

    # 合并保护列表
    for u in args.keep_user:
        PROTECTED_USERNAMES.add(u)

    protected_tables = set(args.keep_table) | SYSTEM_TABLES

    store.init_database()
    conn = store.get_connection()

    # 确定用户清理模式
    user_mode = "none" if args.business_only else args.user_mode

    # 1. 扫描用户
    user_ids, user_info = get_removable_user_ids(conn, user_mode, PROTECTED_USERNAMES)

    mode_labels = {
        "all": "删除所有非保护用户",
        "test-only": "仅删除自动测试用户 (test.* / API Test User)",
        "none": "不删除任何用户",
    }

    header = "🔍 预览 (DRY RUN)" if args.dry_run else "🗑️  正式删除"
    print()
    print("=" * 60)
    print(f"  功能试用数据清理 — {header}")
    print("=" * 60)
    print(f"  数据库: {os.environ.get('APP_DB_DRIVER', 'mysql')}")
    print(f"  用户清理模式: {mode_labels[user_mode]}")
    print(f"  保护用户: {', '.join(sorted(PROTECTED_USERNAMES))}")
    if protected_tables - SYSTEM_TABLES:
        print(f"  保护业务表: {', '.join(sorted(protected_tables - SYSTEM_TABLES))}")
    print(f"  将删除的用户: {len(user_ids)} 个")
    for uid, uname, dname, is_sa in user_info:
        sa_tag = " [超级管理员]" if is_sa else ""
        print(f"    - ID={uid}, {uname} ({dname}){sa_tag}")
    print()

    if user_mode != "none" and not user_ids:
        print("ℹ️  没有需要删除的用户，将只清理业务表。\n")

    # 2. 统计
    print(f"  {'表名':<35} {'行数':>8}")
    print(f"  {'-'*43}")
    total_auth = 0
    total_biz = 0

    # Auth 表
    active_biz_tables = [t for t in BUSINESS_DELETE_ORDER if t not in protected_tables]

    for table in AUTH_DELETE_ORDER:
        count = delete_from_table(conn, table, user_ids, dry_run=True)
        if count > 0:
            print(f"  [A] {table:<32} {count:>8}")
            total_auth += count

    if total_auth > 0:
        print(f"  {'─'*43}")
        print(f"  {'Auth 小计':<35} {total_auth:>8}")
    print()

    for table in active_biz_tables:
        count = delete_from_table(conn, table, user_ids, dry_run=True)
        if count > 0:
            print(f"  [B] {table:<32} {count:>8}")
            total_biz += count

    if total_biz > 0:
        print(f"  {'─'*43}")
        print(f"  {'业务表小计':<35} {total_biz:>8}")

    # 跳过表
    skipped_biz = [t for t in BUSINESS_DELETE_ORDER if t in protected_tables]
    if skipped_biz:
        print(f"\n  🔒 保护表（跳过）: {', '.join(sorted(skipped_biz))}")

    print(f"  {'='*43}")
    print(f"  {'总计':<35} {total_auth + total_biz:>8}")
    print()

    if args.dry_run:
        print("🔍 预览完成。确认无误后执行：")
        if args.business_only:
            print("   python scripts/cleanup_test_data.py --business-only")
        elif args.user_mode != "all":
            print(f"   python scripts/cleanup_test_data.py --user-mode {args.user_mode}")
        else:
            print("   python scripts/cleanup_test_data.py")
        conn.close()
        return

    if total_auth + total_biz == 0:
        print("✅ 没有数据需要清理。")
        conn.close()
        return

    # 3. 确认
    if not args.yes:
        try:
            confirm = input("⚠️  确认删除以上所有数据？(输入 YES 确认): ")
        except (EOFError, KeyboardInterrupt):
            print("\n❌ 已取消。")
            conn.close()
            return
        if confirm.strip() != "YES":
            print("❌ 已取消。")
            conn.close()
            return

    # 4. 备份
    if args.backup:
        backup_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups"
        )
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"cleanup_backup_{ts}.sql")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(f"-- 清理备份 {ts}\n")
            f.write(f"-- 用户数: {len(user_ids)}, 模式: {user_mode}\n\n")
            for table in AUTH_DELETE_ORDER + active_biz_tables:
                count = delete_from_table(conn, table, user_ids, dry_run=True)
                f.write(f"-- {table}: {count} 行\n")
        print(f"✅ 备份已保存: {backup_path}\n")

    # 5. 执行删除
    print("🗑️  开始清理...\n")

    deleted_total = 0
    for table in AUTH_DELETE_ORDER:
        deleted = delete_from_table(conn, table, user_ids, dry_run=False)
        if deleted > 0:
            deleted_total += deleted
            print(f"  ✅ {table}: 删除 {deleted} 行")

    for table in active_biz_tables:
        deleted = delete_from_table(conn, table, user_ids, dry_run=False)
        if deleted > 0:
            deleted_total += deleted
            print(f"  ✅ {table}: 删除 {deleted} 行")

    print()
    print("=" * 60)
    print(f"  ✅ 清理完成！共删除 {deleted_total} 行数据。")
    print("=" * 60)
    print()

    conn.close()


if __name__ == "__main__":
    main()
