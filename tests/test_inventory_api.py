import os
import tempfile
import unittest

from fastapi.testclient import TestClient

import app.db.store as store
from backend.main import app
from tests.auth_api_utils import auth_headers_for_permissions


INVENTORY_TEST_PERMISSIONS = [
    "daily_check:create",
    "inventory:view",
    "inventory:create",
    "inventory:update",
    "inventory:delete",
    "inventory:export",
]


class InventoryApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "inventory-api-test.db")
        store._connection = None
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()
        self.client.headers.update(auth_headers_for_permissions(self.client, INVENTORY_TEST_PERMISSIONS))

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)
        store.close_connection()
        store.DB_DIR = self.original_db_dir
        store.DB_PATH = self.original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def test_balances_endpoint_reflects_daily_intake_stock_in(self):
        self.client.post(
            "/api/daily-intake/items",
            json={
                "intake_date": "2026-04-22",
                "name": "青椒",
                "category": "vegetable",
                "quantity": 6,
                "unit": "斤",
                "source": "manual",
                "transcript": "",
            },
        )

        response = self.client.get("/api/inventory/balances")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["normalized_name"], "青椒")
        self.assertEqual(body["items"][0]["available_quantity"], 6.0)

    def test_outbound_create_update_and_delete(self):
        self.client.post(
            "/api/daily-intake/items",
            json={
                "intake_date": "2026-04-22",
                "name": "土豆",
                "category": "vegetable",
                "quantity": 10,
                "unit": "斤",
                "source": "manual",
                "transcript": "",
            },
        )

        created = self.client.post(
            "/api/inventory/outbound",
            json={
                "business_date": "2026-04-22",
                "name": "土豆",
                "unit": "斤",
                "quantity": 3,
                "note": "领用",
            },
        )
        self.assertEqual(created.status_code, 200)
        transaction_id = created.json()["transaction"]["id"]

        updated = self.client.put(
            f"/api/inventory/outbound/{transaction_id}",
            json={
                "business_date": "2026-04-22",
                "name": "土豆",
                "unit": "斤",
                "quantity": 4,
                "note": "改为 4 斤",
            },
        )
        self.assertEqual(updated.status_code, 200)

        balances_after_update = self.client.get("/api/inventory/balances")
        self.assertEqual(balances_after_update.status_code, 200)
        self.assertEqual(balances_after_update.json()["items"][0]["available_quantity"], 6.0)

        deleted = self.client.delete(f"/api/inventory/outbound/{transaction_id}")
        self.assertEqual(deleted.status_code, 200)

        balances_after_delete = self.client.get("/api/inventory/balances")
        self.assertEqual(balances_after_delete.status_code, 200)
        self.assertEqual(balances_after_delete.json()["items"][0]["available_quantity"], 10.0)

    def test_adjustment_endpoint_retargets_balance(self):
        self.client.post(
            "/api/daily-intake/items",
            json={
                "intake_date": "2026-04-22",
                "name": "豆腐",
                "category": "vegetable",
                "quantity": 8,
                "unit": "板",
                "source": "manual",
                "transcript": "",
            },
        )

        created = self.client.post(
            "/api/inventory/adjustments",
            json={
                "business_date": "2026-04-22",
                "name": "豆腐",
                "unit": "板",
                "target_quantity": 5,
                "note": "盘点后修正",
            },
        )
        self.assertEqual(created.status_code, 200)

        balances = self.client.get("/api/inventory/balances")
        self.assertEqual(balances.status_code, 200)
        self.assertEqual(balances.json()["items"][0]["available_quantity"], 5.0)

    def test_transactions_can_filter_adjustments_only(self):
        self.client.post(
            "/api/daily-intake/items",
            json={
                "intake_date": "2026-04-22",
                "name": "豆腐",
                "category": "vegetable",
                "quantity": 8,
                "unit": "板",
                "source": "manual",
                "transcript": "",
            },
        )
        self.client.post(
            "/api/inventory/outbound",
            json={
                "business_date": "2026-04-22",
                "name": "豆腐",
                "unit": "板",
                "quantity": 2,
                "note": "领用",
            },
        )
        self.client.post(
            "/api/inventory/adjustments",
            json={
                "business_date": "2026-04-22",
                "name": "豆腐",
                "unit": "板",
                "target_quantity": 9,
                "note": "盘点修正",
            },
        )

        response = self.client.get("/api/inventory/transactions", params={"source_type": "manual_adjust"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["source_type"], "manual_adjust")
        self.assertEqual(body["items"][0]["direction"], "ADJUST")
        self.assertEqual(body["items"][0]["target_quantity"], 9.0)

    def test_balance_export_returns_csv(self):
        self.client.post(
            "/api/daily-intake/items",
            json={
                "intake_date": "2026-04-22",
                "name": "青椒",
                "category": "vegetable",
                "quantity": 6,
                "unit": "斤",
                "source": "manual",
                "transcript": "",
            },
        )

        response = self.client.get("/api/inventory/export/balances")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn("inventory-balances.csv", response.headers["content-disposition"])
        self.assertIn("青椒", response.text)

    def test_outbound_rejects_when_stock_is_insufficient(self):
        self.client.post(
            "/api/daily-intake/items",
            json={
                "intake_date": "2026-04-22",
                "name": "鸡翅",
                "category": "meat",
                "quantity": 2,
                "unit": "箱",
                "source": "manual",
                "transcript": "",
            },
        )

        response = self.client.post(
            "/api/inventory/outbound",
            json={
                "business_date": "2026-04-22",
                "name": "鸡翅",
                "unit": "箱",
                "quantity": 5,
                "note": "超额领用",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("库存不足", response.json()["detail"])

    def test_balances_endpoint_requires_authentication(self):
        self.client.headers.clear()

        response = self.client.get("/api/inventory/balances")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "AUTH_REQUIRED")

    def test_outbound_endpoint_requires_create_permission(self):
        self.client.headers.clear()
        self.client.headers.update(auth_headers_for_permissions(self.client, ["daily_check:create", "inventory:view"]))

        response = self.client.post(
            "/api/inventory/outbound",
            json={
                "business_date": "2026-04-22",
                "name": "potato",
                "unit": "kg",
                "quantity": 1,
                "note": "",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "PERMISSION_DENIED")
