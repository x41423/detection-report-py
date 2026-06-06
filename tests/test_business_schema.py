"""Verify that all business-extension tables (v3 migration) create successfully."""
from __future__ import annotations

import pytest

from app.db import store
from app.db.store import get_connection, query_one

EXPECTED_TABLES = [
    "Supplier",
    "PurchaseInRecord",
    "PurchaseInItem",
    "PurchaseReturnRecord",
    "PurchaseReturnItem",
    "OrderRecord",
    "OrderItem",
    "OrderAfterSale",
    "SupplierSettlement",
    "PriceLockRule",
    "PriceLockRuleItem",
    "Coupon",
    "DeliveryRoute",
    "DeliveryTask",
    "SortingTask",
    "SortingPerformance",
    "ProcessingPlan",
    "PointsRecord",
    "OperationTimeConfig",
    "FreightTemplate",
]


def test_all_business_tables_exist():
    """Every expected table should exist after _init_schema() runs."""
    store.init_database()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        existing = {row["name"] for row in cursor.fetchall()}
    finally:
        cursor.close()

    missing = [t for t in EXPECTED_TABLES if t not in existing]
    assert missing == [], f"Missing tables: {missing}"


def test_supplier_table_columns():
    store.init_database()
    row = query_one("SELECT * FROM Supplier LIMIT 0")
    # query_one returns None for empty result set; we only care the table shape exists
    # Just verify the table is queryable
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(Supplier)")
        cols = {r["name"] for r in cursor.fetchall()}
    finally:
        cursor.close()

    expected = {"id", "code", "name", "contact_person", "contact_phone",
                "contact_address", "settlement_method", "status", "remark",
                "created_at", "updated_at"}
    assert expected.issubset(cols), f"Supplier missing columns: {expected - cols}"


def test_purchase_in_record_foreign_key():
    store.init_database()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA foreign_key_list(PurchaseInRecord)")
        fks = {r["table"]: r["from"] for r in cursor.fetchall()}
    finally:
        cursor.close()

    assert "Supplier" in fks, "PurchaseInRecord missing FK to Supplier"
    assert fks["Supplier"] == "supplier_id"


def test_order_record_columns_count():
    store.init_database()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(OrderRecord)")
        cols = [r["name"] for r in cursor.fetchall()]
    finally:
        cursor.close()

    # OrderRecord should have 25+ columns (matching the 37-column Guanmai order list)
    assert len(cols) >= 25, f"OrderRecord has {len(cols)} columns, expected >= 25"


def test_migration_version_recorded():
    store.init_database()
    row = query_one(
        "SELECT * FROM schema_migrations WHERE version = 3 AND name = 'business_schema'"
    )
    assert row is not None, "Migration v3 'business_schema' not recorded"
