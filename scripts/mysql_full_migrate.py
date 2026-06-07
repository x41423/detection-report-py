#!/usr/bin/env python3
"""Auto-migrate ALL tables from SQLite to MySQL — including missing tables.

Usage:
  MYSQL_ROOT_PASSWORD=xxx python scripts/mysql_full_migrate.py
  python scripts/mysql_full_migrate.py --root-password xxx
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
from app.db.mysql_schema import create_mysql_schema, MYSQL_SCHEMA_STATEMENTS

# ── Config ──────────────────────────────────────────────────────────
paths = get_project_paths()
SQLITE_PATH = str(paths.database_file)
MYSQL_HOST = os.getenv("APP_DB_MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("APP_DB_MYSQL_PORT", "3306"))
MYSQL_DB = os.getenv("APP_DB_MYSQL_DATABASE", "inspection_report")
MYSQL_USER = os.getenv("APP_DB_MYSQL_USER", "inspection_app")
MYSQL_PASSWORD = os.getenv("APP_DB_MYSQL_PASSWORD", "")
ROOT_USER = os.getenv("MYSQL_ROOT_USER", "root")

# SQLite → MySQL type mapping
TYPE_MAP = {
    "INTEGER": "BIGINT",
    "INT": "INT",
    "TEXT": "LONGTEXT",
    "REAL": "DOUBLE",
    "BLOB": "LONGBLOB",
    "NUMERIC": "DECIMAL(20,6)",
    "TIMESTAMP": "TIMESTAMP",
    "DATETIME": "DATETIME",
    "BOOLEAN": "TINYINT(1)",
}


def sqlite_type_to_mysql(col_type: str) -> str:
    """Convert SQLite column type to MySQL equivalent."""
    upper = col_type.upper().split("(")[0].strip()
    for sq, my in TYPE_MAP.items():
        if upper.startswith(sq):
            if "(" in col_type:
                return col_type.replace(sq, my, 1).upper()
            return my
    return "LONGTEXT"


def auto_create_mysql_tables(sqlite_conn: sqlite3.Connection, mysql_cursor) -> list[str]:
    """Read SQLite tables, create missing ones in MySQL. Returns created table names."""
    # Get existing MySQL tables
    mysql_cursor.execute("SHOW TABLES")
    mysql_tables = {r[0] for r in mysql_cursor.fetchall()}

    # Get SQLite tables
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_%'")
    sqlite_tables = [r[0] for r in sqlite_cursor.fetchall()]

    created = []
    for table in sqlite_tables:
        if table.lower() in {t.lower() for t in mysql_tables}:
            continue

        # Get column info from SQLite
        sqlite_cursor.execute(f"PRAGMA table_info(`{table}`)")
        cols = sqlite_cursor.fetchall()

        col_defs = []
        for cid, name, ctype, notnull, default, pk in cols:
            mysql_type = sqlite_type_to_mysql(ctype)
            col_def = f"`{name}` {mysql_type}"
            if pk:
                col_def += " NOT NULL"
                # Check if it's AUTOINCREMENT
                if "auto" in ctype.lower() or "autoincrement" in ctype.lower():
                    col_def = f"`{name}` BIGINT PRIMARY KEY AUTO_INCREMENT"
            elif notnull:
                col_def += " NOT NULL"
            if default is not None:
                if isinstance(default, str):
                    col_def += f" DEFAULT '{default}'"
                else:
                    col_def += f" DEFAULT {default}"
            elif not notnull:
                col_def += " DEFAULT NULL"
            col_defs.append(col_def)

        ddl = f"CREATE TABLE IF NOT EXISTS `{table}` (\n  " + ",\n  ".join(col_defs) + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
        print(f"  Creating: {table} ({len(cols)} cols)")
        try:
            mysql_cursor.execute(ddl)
            created.append(table)
        except Exception as e:
            print(f"  WARNING: {table} — {e}")

    return created


def migrate_all_data(sqlite_conn: sqlite3.Connection, mysql_cursor) -> dict[str, int]:
    """Copy all rows from SQLite to MySQL, table by table."""
    # Ordered to respect foreign keys
    order = [
        "Veg", "Unit", "Category", "Product",
        "DailyIntakeSheet", "DailyIntakeItem", "PriceHistory",
        "WeeklyPriceEntry", "InventoryTransaction", "Config",
        "Supplier", "SupplierSettlement", "SupplierProductPrice",
        "OrderRecord", "OrderItem", "OrderAfterSale",
        "ProductSku",
        "PurchaseInRecord", "PurchaseInItem",
        "PurchaseReturnRecord", "PurchaseReturnItem",
        "Quotation", "QuotationProduct",
        "PriceLockRule", "PriceLockRuleItem",
        "DeliveryRoute", "DeliveryTask", "SortingTask", "SortingPerformance",
        "Coupon", "PointsRecord", "ProcessingPlan",
        "OperationTimeConfig", "FreightTemplate",
        "UserColumnPreference",
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
        "auth_sessions", "auth_pending_logins",
        "auth_refresh_token_grace",
    ]

    counts = {}
    sqlite_cursor = sqlite_conn.cursor()
    for table in order:
        sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not sqlite_cursor.fetchone():
            continue

        sqlite_cursor.execute(f"SELECT * FROM `{table}`")
        rows = sqlite_cursor.fetchall()
        if not rows:
            counts[table] = 0
            continue

        col_names = [d[0] for d in sqlite_cursor.description]
        quoted_cols = ", ".join(f"`{c}`" for c in col_names)
        placeholders = ", ".join(["%s"] * len(col_names))
        sql = f"INSERT INTO `{table}` ({quoted_cols}) VALUES ({placeholders})"

        values = []
        for row in rows:
            vals = []
            for v in row:
                if isinstance(v, bytes):
                    vals.append(v)
                elif v is None:
                    vals.append(None)
                else:
                    vals.append(v)
            values.append(tuple(vals))

        try:
            mysql_cursor.executemany(sql, values)
            counts[table] = len(rows)
        except Exception as e:
            print(f"  ERROR importing {table}: {e}")
            counts[table] = -1

    return counts


def main():
    parser = argparse.ArgumentParser(description="Full SQLite→MySQL migration")
    parser.add_argument("--root-password", default=os.getenv("MYSQL_ROOT_PASSWORD", ""))
    parser.add_argument("--app-password", default=os.getenv("MYSQL_APP_PASSWORD", MYSQL_PASSWORD))
    parser.add_argument("--dry-run", action="store_true", help="Use dryrun DB")
    args = parser.parse_args()

    root_pw = args.root_password.strip()
    app_pw = args.app_password.strip()
    db_name = "inspection_report_dryrun" if args.dry_run else MYSQL_DB

    if not root_pw:
        print("ERROR: Set MYSQL_ROOT_PASSWORD env var or pass --root-password")
        sys.exit(1)
    if not app_pw:
        print("WARNING: No app password set. Generating random...")
        import secrets
        app_pw = secrets.token_urlsafe(16)

    # ── 1. Setup MySQL database ──
    print(f"=== Setup: Connecting as root to {MYSQL_HOST}:{MYSQL_PORT} ===")
    root_conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=ROOT_USER, password=root_pw, charset="utf8mb4")
    try:
        with root_conn.cursor() as c:
            c.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            c.execute(f"CREATE USER IF NOT EXISTS '{MYSQL_USER}'@'localhost' IDENTIFIED BY %s", (app_pw,))
            c.execute(f"ALTER USER '{MYSQL_USER}'@'localhost' IDENTIFIED BY %s", (app_pw,))
            c.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{MYSQL_USER}'@'localhost'")
            c.execute("FLUSH PRIVILEGES")
        root_conn.commit()
        print(f"  Database '{db_name}' ready, user '{MYSQL_USER}' configured")
    finally:
        root_conn.close()

    # ── 2. Connect as app user ──
    print(f"\n=== Step 1: Creating schema ===")
    mysql_conn = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=app_pw, database=db_name, charset="utf8mb4")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    try:
        with mysql_conn.cursor() as c:
            # Create tables from existing MYSQL_SCHEMA_STATEMENTS
            for stmt in MYSQL_SCHEMA_STATEMENTS:
                try:
                    c.execute(stmt)
                except Exception as e:
                    print(f"  Schema warning: {str(e)[:100]}")

            # Auto-create missing tables from SQLite
            print("\n=== Step 2: Auto-creating missing MySQL tables ===")
            created = auto_create_mysql_tables(sqlite_conn, c)
            print(f"  Created {len(created)} new tables: {created}")

        mysql_conn.commit()

        # ── 3. Migrate data ──
        print(f"\n=== Step 3: Migrating data ===")
        with mysql_conn.cursor() as c:
            c.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                counts = migrate_all_data(sqlite_conn, c)
            finally:
                c.execute("SET FOREIGN_KEY_CHECKS = 1")
        mysql_conn.commit()

        # ── 4. Verify ──
        print(f"\n=== Migration Results ===")
        total = 0
        for table, count in sorted(counts.items()):
            status = "✅" if count >= 0 else "❌"
            print(f"  {status} {table}: {count} rows")
            if count > 0:
                total += count
        print(f"\n  Total rows migrated: {total}")

        # Row count verification
        print(f"\n=== Step 4: Row count verification ===")
        sqlite_cur = sqlite_conn.cursor()
        with mysql_conn.cursor() as c:
            for table in sorted(counts.keys()):
                if counts[table] < 0:
                    continue
                sqlite_cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                sqlite_count = sqlite_cur.fetchone()[0]
                c.execute(f"SELECT COUNT(*) FROM `{table}`")
                mysql_count = c.fetchone()[0]
                match = "✅" if sqlite_count == mysql_count else "❌ MISMATCH"
                if sqlite_count != mysql_count:
                    print(f"  {match} {table}: SQLite={sqlite_count}, MySQL={mysql_count}")

    finally:
        sqlite_conn.close()
        mysql_conn.close()

    print(f"\n=== Migration complete! ===")
    if not args.dry_run:
        print(f"Set env: APP_DB_DRIVER=mysql APP_DB_MYSQL_PASSWORD=<password>")


if __name__ == "__main__":
    main()
