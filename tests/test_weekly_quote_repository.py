import unittest
import tempfile
import os

from app.db import store


class TestWeeklyQuoteRepository(unittest.TestCase):
    def setUp(self):
        self._original_db_path = store.DB_PATH
        self.tmp = tempfile.mkdtemp()
        store.DB_PATH = os.path.join(self.tmp, "test.db")
        store._connection = None
        store.init_database()
        from app.db.weekly_quote_repository import WeeklyQuoteRepository
        self.repo = WeeklyQuoteRepository()

    def tearDown(self):
        store.DB_PATH = self._original_db_path
        store._connection = None
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_and_list_batches(self):
        batch = self.repo.save_batch("勾庄", "2026-05-07", [
            {"name": "大白菜", "unit": "斤", "price": 0.8},
            {"name": "西红柿", "unit": "斤", "price": 2.5},
        ], source_label="手动录入")
        self.assertEqual(batch["supplier"], "勾庄")
        self.assertEqual(batch["quote_date"], "2026-05-07")
        self.assertIn("entries", batch)
        self.assertEqual(len(batch["entries"]), 2)
        self.assertEqual(batch["entry_count"], 2)

        batches = self.repo.list_batches("勾庄")
        self.assertEqual(len(batches), 1)

    def test_upsert_batch_replaces_entries(self):
        self.repo.save_batch("勾庄", "2026-05-07", [
            {"name": "大白菜", "unit": "斤", "price": 0.8},
        ])
        self.repo.save_batch("勾庄", "2026-05-07", [
            {"name": "大白菜", "unit": "斤", "price": 0.9},
            {"name": "西红柿", "unit": "斤", "price": 2.5},
        ])
        batches = self.repo.list_batches("勾庄")
        self.assertEqual(len(batches), 1)
        batch = batches[0]
        self.assertEqual(len(batch["entries"]), 2)
        cabbage = next(e for e in batch["entries"] if e["name"] == "大白菜")
        self.assertEqual(cabbage["price"], 0.9)

    def test_weekly_highest_price(self):
        self.repo.save_batch("勾庄", "2026-05-06", [
            {"name": "大白菜", "unit": "斤", "price": 0.9},
        ])
        self.repo.save_batch("勾庄", "2026-05-07", [
            {"name": "大白菜", "unit": "斤", "price": 0.8},
        ])
        summary = self.repo.get_weekly_summary("勾庄", "2026-05-07")
        cabbage = next((i for i in summary if i["name"] == "大白菜"), None)
        self.assertIsNotNone(cabbage)
        self.assertEqual(cabbage["summary_price"], 0.9)

    def test_delete_batch(self):
        self.repo.save_batch("勾庄", "2026-05-07", [
            {"name": "大白菜", "unit": "斤", "price": 0.8},
        ])
        self.assertTrue(self.repo.delete_batch("勾庄", "2026-05-07"))
        batches = self.repo.list_batches("勾庄")
        self.assertEqual(len(batches), 0)

    def test_get_all_suppliers(self):
        self.repo.save_batch("勾庄", "2026-05-07", [
            {"name": "大白菜", "unit": "斤", "price": 0.8},
        ])
        self.repo.save_batch("豆制品", "2026-05-07", [
            {"name": "老豆腐", "unit": "斤", "price": 2.5},
        ])
        suppliers = self.repo.get_all_suppliers()
        self.assertIn("勾庄", suppliers)
        self.assertIn("豆制品", suppliers)

    def test_get_entries_by_date_range(self):
        self.repo.save_batch("勾庄", "2026-05-06", [
            {"name": "大白菜", "unit": "斤", "price": 0.9},
        ])
        self.repo.save_batch("勾庄", "2026-05-07", [
            {"name": "西红柿", "unit": "斤", "price": 2.5},
        ])
        self.repo.save_batch("勾庄", "2026-05-08", [
            {"name": "黄瓜", "unit": "斤", "price": 1.3},
        ])
        entries = self.repo.get_entries("勾庄", "2026-05-06", "2026-05-07")
        names = {e["name"] for e in entries}
        self.assertIn("大白菜", names)
        self.assertIn("西红柿", names)
        self.assertNotIn("黄瓜", names)


if __name__ == "__main__":
    unittest.main()
