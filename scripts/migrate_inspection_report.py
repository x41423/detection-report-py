"""Migration: add InspectionReport and InspectionReportProduct tables.

Safe for existing databases — uses CREATE TABLE IF NOT EXISTS.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

MIGRATION_ID = "inspection_report_v1"
MIGRATION_LABEL = "检测报告归档表"


def check(conn: sqlite3.Connection) -> bool:
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(InspectionReport)")
        columns = {row[1] for row in cursor.fetchall()}
        return "report_no" in columns
    except Exception:
        return False


def run(conn: sqlite3.Connection) -> bool:
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS InspectionReport (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL DEFAULT '',
                file_url TEXT NOT NULL DEFAULT '',
                test_date TEXT NOT NULL DEFAULT '',
                valid_from TEXT NOT NULL DEFAULT '',
                valid_until TEXT NOT NULL DEFAULT '',
                supplier_id INTEGER DEFAULT 0,
                submit_org TEXT NOT NULL DEFAULT '',
                test_org TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                source TEXT NOT NULL DEFAULT 'manual',
                pesticide_task_id INTEGER DEFAULT 0,
                uploaded_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ir_report_no ON InspectionReport(report_no)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ir_supplier ON InspectionReport(supplier_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ir_status ON InspectionReport(status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ir_test_date ON InspectionReport(test_date)"
        )

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS InspectionReportProduct (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL REFERENCES InspectionReport(id),
                sku_id INTEGER NOT NULL DEFAULT 0,
                product_id INTEGER NOT NULL DEFAULT 0,
                batch TEXT NOT NULL DEFAULT ''
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_irp_report ON InspectionReportProduct(report_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_irp_sku ON InspectionReportProduct(sku_id)"
        )

        conn.commit()
        logger.info("Migration %s applied successfully", MIGRATION_ID)
        return True
    except Exception as exc:
        logger.error("Migration %s failed: %s", MIGRATION_ID, exc)
        conn.rollback()
        return False
