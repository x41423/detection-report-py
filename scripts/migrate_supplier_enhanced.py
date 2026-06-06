"""Migration: Add enhanced fields to Supplier table.

Adds supplier_type, business_license, tax_number, bank_name, bank_account,
payment_terms, credit_limit, level columns to the existing Supplier table.
"""

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

# Migration metadata
MIGRATION_ID = "supplier_enhanced_v1"
MIGRATION_LABEL = "供应商表增强字段"


def check(conn: sqlite3.Connection) -> bool:
    """Check if this migration has been applied."""
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Supplier)")
        columns = {row[1] for row in cursor.fetchall()}
        return "supplier_type" in columns
    except Exception:
        return False


def run(conn: sqlite3.Connection) -> bool:
    """Apply this migration."""
    try:
        cursor = conn.cursor()

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(Supplier)")
        columns = {row[1] for row in cursor.fetchall()}

        # Add new columns if they don't exist
        new_columns = [
            ("supplier_type", "TEXT DEFAULT 'enterprise'"),
            ("business_license", "TEXT"),
            ("tax_number", "TEXT"),
            ("bank_name", "TEXT"),
            ("bank_account", "TEXT"),
            ("payment_terms", "TEXT"),
            ("credit_limit", "REAL DEFAULT 0"),
            ("level", "TEXT DEFAULT 'normal'"),
        ]

        added = 0
        for col_name, col_def in new_columns:
            if col_name not in columns:
                cursor.execute(f"ALTER TABLE Supplier ADD COLUMN {col_name} {col_def}")
                added += 1
                logger.info(f"Added column Supplier.{col_name}")

        if added > 0:
            conn.commit()
            logger.info(f"Migration {MIGRATION_ID}: added {added} columns")
        else:
            logger.info(f"Migration {MIGRATION_ID}: all columns already exist")

        return True
    except Exception as e:
        logger.error(f"Migration {MIGRATION_ID} failed: {e}")
        conn.rollback()
        return False


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from app.db.store import get_connection

    logging.basicConfig(level=logging.INFO)

    conn = get_connection()
    if check(conn):
        print("Migration already applied")
    else:
        if run(conn):
            print("Migration applied successfully")
        else:
            print("Migration failed")
            sys.exit(1)
