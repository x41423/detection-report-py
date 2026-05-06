import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.utils import data_generator
from shared.pesticide_data import (
    DataGeneratorService,
    format_json_data,
    parse_json_data,
    parse_vegetable_list,
    remove_duplicate_varieties,
)


class PesticideDataTests(unittest.TestCase):
    def test_parse_vegetable_list_supports_comma_and_newline(self):
        self.assertEqual(parse_vegetable_list("白菜, 菠菜，生菜"), ["白菜", "菠菜", "生菜"])
        self.assertEqual(parse_vegetable_list("白菜\n菠菜\n生菜"), ["白菜", "菠菜", "生菜"])

    def test_parse_vegetable_list_deduplicates(self):
        self.assertEqual(parse_vegetable_list("白菜, 白菜, 菠菜"), ["白菜", "菠菜"])
        self.assertEqual(parse_vegetable_list("白菜\n白菜\n菠菜"), ["白菜", "菠菜"])
        self.assertEqual(parse_vegetable_list("白菜, 菠菜, 白菜, 菠菜"), ["白菜", "菠菜"])
        self.assertEqual(parse_vegetable_list("白菜\n白菜\n白菜"), ["白菜"])

    def test_parse_json_data_rejects_non_list_payload(self):
        with self.assertRaises(ValueError):
            parse_json_data('{"variety": "白菜"}')

    def test_remove_duplicate_varieties_keeps_first_occurrence(self):
        unique, removed = remove_duplicate_varieties(
            [
                {"variety": "白菜", "rate": "1.000%"},
                {"variety": "菠菜", "rate": "2.000%"},
                {"variety": "白菜", "rate": "3.000%"},
            ]
        )

        self.assertEqual(removed, 1)
        self.assertEqual(
            unique,
            [
                {"variety": "白菜", "rate": "1.000%"},
                {"variety": "菠菜", "rate": "2.000%"},
            ],
        )

    def test_service_reuses_history_within_five_percent_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            history_path.write_text(
                json.dumps(
                    {
                        "high": [],
                        "low": [10.0],
                        "other": [],
                        "variety_rates": {"黄瓜": 10.0},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            service = DataGeneratorService(
                high_risk=[],
                low_risk=["黄瓜"],
                rate_ranges={
                    "low": {"min": 0.5, "max": 15.0, "mean": 6.0, "std": 2.0},
                    "other": {"min": 5.0, "max": 40.0, "mean": 20.0, "std": 8.0},
                },
                history_file=history_path,
            )

            with patch("shared.pesticide_data.random.uniform", return_value=10.3), patch(
                "shared.pesticide_data.random.random", return_value=0.7
            ):
                result = service.generate_rates(["黄瓜"])

            self.assertEqual(result, [{"variety": "黄瓜", "rate": "10.300%"}])
            stored = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertAlmostEqual(stored["variety_rates"]["黄瓜"], 10.3, places=3)

    def test_service_avoids_integer_rates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            service = DataGeneratorService(
                high_risk=[],
                low_risk=[],
                rate_ranges={
                    "other": {"min": 5.0, "max": 40.0, "mean": 20.0, "std": 8.0},
                },
                history_file=Path(tmpdir) / "history.json",
            )

            with patch("shared.pesticide_data.random.gauss", return_value=20.0), patch(
                "shared.pesticide_data.random.uniform", return_value=0.2
            ), patch("shared.pesticide_data.random.random", return_value=0.8):
                result = service.generate_rates(["生菜"])

            self.assertEqual(result, [{"variety": "生菜", "rate": "20.200%"}])

    def test_legacy_app_wrapper_remains_compatible(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            history_path = Path(tmpdir) / "history.json"
            data_generator.HISTORY_FILE = str(history_path)
            data_generator.set_risk_lists([], ["黄瓜"])
            data_generator.set_rate_ranges(
                {
                    "low": {"min": 0.5, "max": 15.0, "mean": 6.0, "std": 2.0},
                    "other": {"min": 5.0, "max": 40.0, "mean": 20.0, "std": 8.0},
                }
            )

            with patch("shared.pesticide_data.random.gauss", return_value=6.0), patch(
                "shared.pesticide_data.random.uniform", return_value=0.15
            ), patch("shared.pesticide_data.random.random", return_value=0.9):
                result = data_generator.gen_inhibition_rates(["黄瓜"])

            self.assertEqual(result, [{"variety": "黄瓜", "rate": "6.150%"}])
            self.assertEqual(
                format_json_data(result),
                '[\n  {\n    "variety": "黄瓜",\n    "rate": "6.150%"\n  }\n]',
            )


if __name__ == "__main__":
    unittest.main()

