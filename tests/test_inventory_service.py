import os
import tempfile
import unittest

import app.db.store as store
from backend.services.daily_intake_service import DailyIntakeService
from backend.services.inventory_service import InventoryService


class InventoryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "inventory-service-test.db")
        store._connection = None
        store.init_database()
        self.daily_intake_service = DailyIntakeService()
        self.inventory_service = InventoryService()

    def tearDown(self):
        store.close_connection()
        store.DB_DIR = self.original_db_dir
        store.DB_PATH = self.original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def test_daily_intake_item_creates_inventory_balance(self):
        self.daily_intake_service.add_item("2026-04-22", "土豆", "vegetable", 5, "斤")

        balances = self.inventory_service.list_balances()

        self.assertEqual(balances["total"], 1)
        self.assertEqual(balances["items"][0]["normalized_name"], "土豆")
        self.assertEqual(balances["items"][0]["available_quantity"], 5.0)

    def test_daily_intake_update_and_delete_keep_inventory_in_sync(self):
        created = self.daily_intake_service.add_item("2026-04-22", "白菜", "vegetable", 5, "斤")
        item_id = created["item"]["id"]

        self.daily_intake_service.update_item(
            item_id,
            name="白菜",
            category="vegetable",
            quantity=8,
            unit="斤",
            source="manual",
            transcript="",
        )
        balances_after_update = self.inventory_service.list_balances()
        self.assertEqual(balances_after_update["items"][0]["available_quantity"], 8.0)

        self.daily_intake_service.delete_item(item_id)
        balances_after_delete = self.inventory_service.list_balances()
        self.assertEqual(balances_after_delete["total"], 0)

    def test_outbound_rejects_when_quantity_exceeds_balance(self):
        self.daily_intake_service.add_item("2026-04-22", "鸡腿", "meat", 3, "箱")

        with self.assertRaisesRegex(ValueError, "库存不足"):
            self.inventory_service.create_outbound(
                business_date="2026-04-22",
                name="鸡腿",
                unit="箱",
                quantity=5,
                note="测试超额出库",
            )

    def test_adjustment_sets_target_balance_and_delete_rolls_back(self):
        self.daily_intake_service.add_item("2026-04-22", "豆腐", "vegetable", 10, "板")

        created = self.inventory_service.create_adjustment(
            business_date="2026-04-22",
            name="豆腐",
            unit="板",
            target_quantity=4,
            note="盘点修正",
        )
        self.assertEqual(created["transaction"]["direction"], "ADJUST")
        balances_after_adjust = self.inventory_service.list_balances()
        self.assertEqual(balances_after_adjust["items"][0]["available_quantity"], 4.0)

        self.inventory_service.delete_adjustment(created["transaction"]["id"])
        balances_after_delete = self.inventory_service.list_balances()
        self.assertEqual(balances_after_delete["items"][0]["available_quantity"], 10.0)
