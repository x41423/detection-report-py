"""
Supplier → Merchant 精简迁移脚本 (v2)
======================================
仅重命名表名，保留所有列名（supplier_id 不变），
同时创建全新的 Supplier 表用于真正的供应商管理。

执行方式: python scripts/migrate_supplier_to_merchant.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "data" / "app.db"


def rename_table(cursor: sqlite3.Cursor, old: str, new: str) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (old,))
    if not cursor.fetchone():
        print(f"  ⏭  {old} 不存在，跳过")
        return False
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (new,))
    if cursor.fetchone():
        print(f"  ⚠️  {new} 已存在，跳过")
        return False
    cursor.execute(f"ALTER TABLE {old} RENAME TO {new}")
    print(f"  ✅ {old} → {new}")
    return True


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    cursor = conn.cursor()

    print("=" * 60)
    print("Supplier → Merchant 迁移 (v2 — 仅重命名表)")
    print("=" * 60)

    # Phase 1: Rename main table
    print("\n📦 Phase 1: 重命名主表")
    renamed = rename_table(cursor, "Supplier", "Merchant")

    # Phase 2: Rename dependent tables
    print("\n📦 Phase 2: 重命名依赖表")
    rename_table(cursor, "SupplierProductPrice", "MerchantProductPrice")
    rename_table(cursor, "SupplierSettlement", "MerchantSettlement")
    rename_table(cursor, "WeeklyQuoteSupplierConfig", "WeeklyQuoteMerchantConfig")

    # Phase 3: Create new Supplier table for real suppliers
    print("\n📦 Phase 3: 创建新 Supplier 表")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Supplier (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_code   TEXT NOT NULL UNIQUE,
            name            TEXT NOT NULL,
            company_name    TEXT DEFAULT '',
            contact_address TEXT DEFAULT '',
            remark          TEXT DEFAULT '',
            default_purchaser TEXT DEFAULT '',
            linked_station    TEXT DEFAULT '',
            settlement_cycle          TEXT DEFAULT '日结',
            invoice_type              TEXT DEFAULT '普票或无票',
            sales_purchase_settlement INTEGER DEFAULT 0,
            business_license   TEXT DEFAULT '',
            bank_account_name  TEXT DEFAULT '',
            bank_name          TEXT DEFAULT '',
            bank_account       TEXT DEFAULT '',
            supplier_nature    TEXT DEFAULT '普通',
            purchase_auto_sync   INTEGER DEFAULT 0,
            geo_location         TEXT DEFAULT '',
            qualification_images TEXT DEFAULT '[]',
            payment_qr           TEXT DEFAULT '',
            status     TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for tbl in ["SupplierCategory", "SupplierProduct", "SupplierContact", "SupplierContract"]:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {tbl} (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER NOT NULL REFERENCES Supplier(id)
            )
        """)
    print("  ✅ 新 Supplier + 4 关联表已创建")

    # Phase 4: Record migration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_version (
            category TEXT, version TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (category, version)
        )
    """)
    cursor.execute(
        "INSERT OR IGNORE INTO app_version (category, version) VALUES (?, ?)",
        ("migration", "supplier_to_merchant_v2"),
    )

    conn.commit()
    conn.close()
    print(f"\n✅ 迁移完成！{'表已重命名' if renamed else '已是最新状态'}")


if __name__ == "__main__":
    migrate()
