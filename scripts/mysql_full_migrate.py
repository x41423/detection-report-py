#!/usr/bin/env python3
"""Auto-migrate ALL tables from SQLite to MySQL — including missing tables.

Usage:
  python scripts/mysql_full_migrate.py --dry-run --app-password xxx
  python scripts/mysql_full_migrate.py --app-password xxx  # formal migration
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import pymysql
from shared.project_paths import get_project_paths
from app.db.mysql_schema import MYSQL_SCHEMA_STATEMENTS

# ── Config ──
paths = get_project_paths()
SQLITE_PATH = str(paths.database_file)
MYSQL_HOST = os.getenv("APP_DB_MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("APP_DB_MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("APP_DB_MYSQL_DATABASE", "inspection_report")
MYSQL_USER = os.getenv("APP_DB_MYSQL_USER", "inspection_app")

TYPE_MAP = {"INTEGER": "BIGINT", "INT": "INT", "TEXT": "LONGTEXT", "REAL": "DOUBLE",
            "BLOB": "LONGBLOB", "TIMESTAMP": "TIMESTAMP", "DATETIME": "DATETIME"}

# 表名映射: SQLite旧名 → MySQL新名
TABLE_RENAME = {
    "Supplier": "Merchant",
    "SupplierSettlement": "MerchantSettlement",
    "SupplierProductPrice": "MerchantProductPrice",
    "WeeklyQuoteSupplierConfig": "WeeklyQuoteMerchantConfig",
}

MIGRATION_ORDER = [
    "Veg", "Unit", "Category", "Product", "ProductSku",
    "Supplier", "SupplierSettlement", "SupplierProductPrice",
    "OrderRecord", "OrderItem", "OrderAfterSale",
    "PurchaseInRecord", "PurchaseInItem",
    "PurchaseReturnRecord", "PurchaseReturnItem",
    "Quotation", "QuotationProduct", "PriceLockRule", "PriceLockRuleItem",
    "DeliveryRoute", "DeliveryTask", "SortingTask", "SortingPerformance",
    "Coupon", "PointsRecord", "ProcessingPlan",
    "OperationTimeConfig", "FreightTemplate",
    "UserColumnPreference",
    "DailyIntakeSheet", "DailyIntakeItem", "PriceHistory",
    "WeeklyPriceEntry", "InventoryTransaction", "Config",
    "WeeklyQuoteBatch", "WeeklyQuoteEntry",
    "WeeklyQuoteMeasureUnitOption", "WeeklyQuoteSupplierConfig",
    "InspectionReport", "InspectionReportProduct",
    "LossReport", "LossReportItem",
    "OrderModification", "PriceMarkup",
    "MigrationVersion", "schema_migrations",
    "auth_users", "auth_roles", "auth_permissions",
    "auth_user_roles", "auth_role_permissions",
    "auth_user_permission_overrides", "auth_permission_requests",
    "auth_devices", "auth_audit_logs",
    "auth_sessions", "auth_pending_logins", "auth_refresh_token_grace",
]


def sqlite_type_to_mysql(col_type: str) -> str:
    upper = col_type.upper().split("(")[0].strip()
    for sq, my in TYPE_MAP.items():
        if upper.startswith(sq):
            return my
    return "LONGTEXT"


def auto_create_missing_tables(sqlite_conn, mysql_cursor) -> list:
    """Try to create every SQLite table in MySQL. Idempotent via IF NOT EXISTS."""
    sqlite_cur = sqlite_conn.cursor()
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_%'")
    sqlite_tables = [r[0] for r in sqlite_cur.fetchall()]

    created = []
    for table in sqlite_tables:
        sqlite_cur.execute(f"PRAGMA table_info(`{table}`)")
        cols = sqlite_cur.fetchall()
        col_defs = []
        for cid, name, ctype, notnull, default, pk in cols:
            mysql_type = sqlite_type_to_mysql(ctype)
            if pk and "autoincrement" in ctype.lower():
                col_defs.append(f"`{name}` BIGINT PRIMARY KEY AUTO_INCREMENT")
            elif pk:
                col_defs.append(f"`{name}` {mysql_type} NOT NULL PRIMARY KEY")
            else:
                col_def = f"`{name}` {mysql_type}"
                if notnull: col_def += " NOT NULL"
                col_defs.append(col_def)
        ddl = f"CREATE TABLE IF NOT EXISTS `{table}` (\n  " + ",\n  ".join(col_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        print(f"  Creating: {table}")
        mysql_cursor.execute(ddl)
        created.append(table)
    return created


def migrate_data(sqlite_conn, mysql_cursor, order) -> dict:
    counts = {}
    sqlite_cur = sqlite_conn.cursor()
    for table in order:
        sqlite_cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not sqlite_cur.fetchone():
            continue
        mysql_table = TABLE_RENAME.get(table, table)  # 映射到MySQL新表名
        sqlite_cur.execute(f"SELECT * FROM `{table}`")
        rows = sqlite_cur.fetchall()
        if not rows:
            counts[table] = 0
            continue
        col_names = [d[0] for d in sqlite_cur.description]
        quoted_cols = ", ".join(f"`{c}`" for c in col_names)
        placeholders = ", ".join(["%s"] * len(col_names))
        sql = f"INSERT INTO `{mysql_table}` ({quoted_cols}) VALUES ({placeholders})"
        values = [tuple(None if v is None else (v.decode() if isinstance(v, bytes) else v) for v in row) for row in rows]
        try:
            mysql_cursor.executemany(sql, values)
            counts[table] = len(rows)
        except Exception as e:
            print(f"  ERROR {table}→{mysql_table}: {str(e)[:80]}")
            counts[table] = -1
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-password", default=os.getenv("MYSQL_APP_PASSWORD", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    app_pw = args.app_password.strip() or os.getenv("APP_DB_MYSQL_PASSWORD", "")
    db_name = "inspection_report_dryrun" if args.dry_run else MYSQL_DB

    if not app_pw:
        print("ERROR: Set --app-password or APP_DB_MYSQL_PASSWORD")
        sys.exit(1)

    print(f"=== Connecting to {MYSQL_HOST}:{MYSQL_PORT}/{db_name} ===")
    mysql_conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=app_pw, database=db_name, charset="utf8mb4")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    try:
        with mysql_conn.cursor() as c:
            # Step 1: Run existing schema
            for stmt in MYSQL_SCHEMA_STATEMENTS:
                try: c.execute(stmt)
                except Exception: pass

            # Step 2: Auto-create missing tables
            print("\n=== Auto-creating missing tables ===")
            created = auto_create_missing_tables(sqlite_conn, c)
            print(f"  Created {len(created)} tables")

            # Step 3: Clear + migrate
            print("\n=== Migrating data ===")
            c.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                for table in MIGRATION_ORDER:
                    mysql_table = TABLE_RENAME.get(table, table)
                    try: c.execute(f"DELETE FROM `{mysql_table}`")
                    except Exception: pass
                counts = migrate_data(sqlite_conn, c, MIGRATION_ORDER)
            finally:
                c.execute("SET FOREIGN_KEY_CHECKS = 1")
        mysql_conn.commit()

        # Step 4: Verify
        print("\n=== Results ===")
        total = 0; mismatches = 0
        sqlite_cur = sqlite_conn.cursor()
        with mysql_conn.cursor() as c:
            for table, count in sorted(counts.items()):
                status = "✅" if count >= 0 else "❌"
                if count > 0:
                    sqlite_cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                    sc = sqlite_cur.fetchone()[0]
                    try:
                        c.execute(f"SELECT COUNT(*) FROM `{table}`")
                        mc = c.fetchone()[0]
                    except Exception:
                        mc = -1
                    if sc != mc:
                        print(f"  {status} {table}: {count} rows (SQLite={sc}, MySQL={mc}) ❗")
                        mismatches += 1
                    else:
                        print(f"  {status} {table}: {count} rows")
                    total += count
                elif count == 0:
                    print(f"  {status} {table}: 0 rows")

        print(f"\n  Total migrated: {total} rows, mismatches: {mismatches}")
        if mismatches:
            print("  ⚠️ Some tables have row count mismatches — check above")

    finally:
        sqlite_conn.close()
        mysql_conn.close()

    print("\n=== Migration complete! ===")


if __name__ == "__main__":
    main()
