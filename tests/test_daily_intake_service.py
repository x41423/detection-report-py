import os
import tempfile
import unittest

import app.db.store as store
from backend.services.daily_intake_service import DailyIntakeService


class DailyIntakeServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "daily-intake-test.db")
        store._connection = None
        store.init_database()
        self.service = DailyIntakeService()

    def tearDown(self):
        store.close_connection()
        store.DB_DIR = self.original_db_dir
        store.DB_PATH = self.original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def test_today_sheet_is_singleton_per_date(self):
        first = self.service.get_today_sheet()
        second = self.service.get_today_sheet()

        self.assertTrue(first["success"])
        self.assertEqual(first["sheet"]["id"], second["sheet"]["id"])
        self.assertEqual(first["sheet"]["intake_date"], second["sheet"]["intake_date"])

    def test_duplicate_items_accumulate_quantity_and_traceability(self):
        first = self.service.add_item("2026-04-15", "土豆", "vegetable", 5, "斤")
        second = self.service.add_item(
            "2026-04-15",
            "土豆",
            "meat",
            3,
            "斤",
            source="voice",
            transcript="土豆三斤",
        )

        self.assertFalse(first["merged"])
        self.assertTrue(second["merged"])
        self.assertEqual(second["sheet"]["item_count"], 1)
        item = second["sheet"]["items"][0]
        self.assertEqual(item["quantity"], 8)
        self.assertEqual(item["category"], "vegetable")
        self.assertEqual(item["last_source"], "voice")
        self.assertEqual(item["last_transcript"], "土豆三斤")
        self.assertEqual(item["merge_count"], 2)

    def test_merge_accumulates_all_transcripts(self):
        self.service.add_item(
            "2026-04-15", "包菜", "vegetable", 100, "斤",
            source="voice", transcript="包菜一百斤",
        )
        second = self.service.add_item(
            "2026-04-15", "包菜", "vegetable", 20, "斤",
            source="voice", transcript="包菜二十斤",
        )

        item = second["sheet"]["items"][0]
        self.assertEqual(item["quantity"], 120)
        self.assertEqual(item["last_transcript"], "包菜二十斤")
        self.assertIn("包菜一百斤", item["transcript"])
        self.assertIn("包菜二十斤", item["transcript"])
        self.assertIn("\n---\n", item["transcript"])

        third = self.service.add_item(
            "2026-04-15", "包菜", "vegetable", 5, "斤",
            source="voice", transcript="包菜五斤",
        )
        item3 = third["sheet"]["items"][0]
        self.assertEqual(item3["quantity"], 125)
        self.assertEqual(item3["last_transcript"], "包菜五斤")
        self.assertEqual(item3["transcript"].count("\n---\n"), 2)

    def test_parse_transcript_returns_merge_preview(self):
        self.service.add_item("2026-04-15", "土豆", "vegetable", 5, "斤")

        result = self.service.parse_transcript("土豆三斤", "2026-04-15")

        self.assertEqual(result["parse_status"], "parsed")
        self.assertEqual(result["draft_name"], "土豆")
        self.assertEqual(result["unit"], "斤")
        self.assertEqual(result["quantity"], 3)
        self.assertIsNotNone(result["merge_preview"])
        self.assertEqual(result["merge_preview"]["next_quantity"], 8)

    def test_parse_transcript_invalid_when_missing_quantity(self):
        result = self.service.parse_transcript("土豆", "2026-04-15")

        self.assertEqual(result["parse_status"], "invalid")
        self.assertTrue(result["warnings"])

    def test_parse_transcript_accepts_jin_homophone_as_unit(self):
        result = self.service.parse_transcript("蘑菇5金", "2026-04-15")

        self.assertEqual(result["parse_status"], "parsed")
        self.assertEqual(result["draft_name"], "蘑菇")
        self.assertEqual(result["unit"], "斤")
        self.assertEqual(result["quantity"], 5)

    def test_parse_transcript_corrects_common_vegetable_homophones(self):
        mushroom = self.service.parse_transcript("平菇3斤", "2026-04-15")
        ginger = self.service.parse_transcript("生将2斤", "2026-04-15")
        celery = self.service.parse_transcript("小西琴4斤", "2026-04-15")

        self.assertEqual(mushroom["parse_status"], "parsed")
        self.assertEqual(mushroom["normalized_name"], "蘑菇")
        self.assertEqual(ginger["normalized_name"], "生姜")
        self.assertEqual(celery["normalized_name"], "小西芹")

    def test_parse_transcript_doubanjiang_yi_tong(self):
        result = self.service.parse_transcript("豆瓣酱一桶", "2026-04-15")

        self.assertEqual(result["parse_status"], "parsed")
        self.assertEqual(result["draft_name"], "豆瓣酱")
        self.assertEqual(result["quantity"], 1.0)
        self.assertEqual(result["unit"], "桶")

    def test_parse_transcript_new_units_recognized(self):
        cases = [
            ("花生酱2罐", "花生酱", 2.0, "罐"),
            ("豆腐3盒", "豆腐", 3.0, "盒"),
            ("腊肉两块", "腊肉", 2.0, "块"),
            ("食用油5升", "食用油", 5.0, "升"),
            ("盐50克", "盐", 50.0, "克"),
        ]
        for transcript, expected_name, expected_qty, expected_unit in cases:
            with self.subTest(transcript=transcript):
                result = self.service.parse_transcript(transcript, "2026-04-15")
                self.assertEqual(result["parse_status"], "parsed", f"解析失败：{transcript}")
                self.assertEqual(result["draft_name"], expected_name)
                self.assertEqual(result["quantity"], expected_qty)
                self.assertEqual(result["unit"], expected_unit)

    def test_normalize_unit_kuang_alias_maps_to_canonical(self):
        result = self.service.parse_transcript("香菜2框", "2026-04-15")

        self.assertEqual(result["parse_status"], "parsed")
        self.assertEqual(result["unit"], "筐")

    def test_history_dates_are_isolated(self):
        self.service.add_item("2026-04-14", "白菜", "vegetable", 2, "斤")
        self.service.add_item("2026-04-15", "鸡腿", "meat", 1, "箱")

        yesterday = self.service.get_sheet("2026-04-14")
        today = self.service.get_sheet("2026-04-15")

        self.assertEqual(yesterday["sheet"]["item_count"], 1)
        self.assertEqual(today["sheet"]["item_count"], 1)
        self.assertEqual(yesterday["sheet"]["items"][0]["raw_name"], "白菜")
        self.assertEqual(today["sheet"]["items"][0]["raw_name"], "鸡腿")


if __name__ == "__main__":
    unittest.main()
