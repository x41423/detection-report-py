import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.weekly_price_service import WeeklyPriceService


class WeeklyPriceServiceTests(unittest.TestCase):
    def test_execute_requires_explicit_output_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            update_path = root / "update.xlsx"
            reference_path = root / "reference.xlsx"
            update_path.write_text("update", encoding="utf-8")
            reference_path.write_text("reference", encoding="utf-8")

            service = WeeklyPriceService()

            with self.assertRaises(ValueError):
                service.execute(
                    update_path=str(update_path),
                    reference_path=str(reference_path),
                    output_path="",
                )

    def test_execute_rejects_missing_output_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            update_path = root / "update.xlsx"
            reference_path = root / "reference.xlsx"
            update_path.write_text("update", encoding="utf-8")
            reference_path.write_text("reference", encoding="utf-8")

            service = WeeklyPriceService()

            with self.assertRaises(FileNotFoundError):
                service.execute(
                    update_path=str(update_path),
                    reference_path=str(reference_path),
                    output_path=str(root / "missing" / "custom-output.xlsx"),
                )

    def test_execute_uses_explicit_output_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            update_path = root / "update.xlsx"
            reference_path = root / "reference.xlsx"
            output_path = root / "exports" / "custom-output.xlsx"
            output_path.parent.mkdir()
            update_path.write_text("update", encoding="utf-8")
            reference_path.write_text("reference", encoding="utf-8")

            with patch("backend.services.weekly_price_service.get_weekly_price_aliases", return_value={}), patch(
                "backend.services.weekly_price_service.update_weekly_prices",
                return_value={
                    "matched_count": 4,
                    "updated_count": 3,
                    "matched_items": [],
                    "not_matched": [],
                    "not_matched_count": 0,
                    "not_matched_unique_count": 0,
                    "alias_hit_count": 0,
                    "warnings": [],
                    "output_path": str(output_path),
                    "backup_path": None,
                },
            ) as update_weekly_prices:
                service = WeeklyPriceService()
                result = service.execute(
                    update_path=str(update_path),
                    reference_path=str(reference_path),
                    output_path=str(output_path),
                )

            update_weekly_prices.assert_called_once_with(
                update_path=str(update_path),
                reference_path=str(reference_path),
                output_path=str(output_path),
                weekly_price_aliases={},
            )
            self.assertTrue(result["success"])
            self.assertEqual(result["output_path"], str(output_path))


if __name__ == "__main__":
    unittest.main()
