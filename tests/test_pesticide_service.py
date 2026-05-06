import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.services.pesticide_service import PesticideService


class PesticideServiceTests(unittest.TestCase):
    def test_generate_rates_refreshes_config_and_uses_generator(self):
        with patch("backend.services.pesticide_service.get_config") as get_config, patch(
            "backend.services.pesticide_service.DataGeneratorService"
        ) as generator_cls:
            generator = MagicMock()
            generator.generate_rates.return_value = [{"variety": "白菜", "rate": "6.150%"}]
            generator_cls.return_value = generator
            get_config.return_value = {
                "high_risk": [],
                "low_risk": ["白菜"],
                "rate_ranges": {"low": {"min": 0.5, "max": 15.0, "mean": 6.0, "std": 2.0}},
            }

            service = PesticideService()
            result = service.generate_rates("白菜")

            self.assertEqual(result, [{"variety": "白菜", "rate": "6.150%"}])
            self.assertEqual(generator_cls.call_count, 2)
            generator.generate_rates.assert_called_once_with(["白菜"])

    def test_execute_task_calls_process_documents_and_updates_inspector(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            big_path = root / "big.docx"
            small_path = root / "small.docx"
            big_path.write_text("big", encoding="utf-8")
            small_path.write_text("small", encoding="utf-8")
            output_dir = root / "output"
            output_dir.mkdir()

            json_text = json.dumps([{"variety": "白菜", "rate": "6.150%"}], ensure_ascii=False)

            with patch("backend.services.pesticide_service.get_config") as get_config, patch(
                "backend.services.pesticide_service.update_config"
            ) as update_config, patch(
                "backend.services.pesticide_service.process_documents"
            ) as process_documents:
                get_config.return_value = {"inspector_name": "旧检查员"}
                service = PesticideService()

                result = service.execute_task(
                    str(big_path),
                    str(small_path),
                    json_text,
                    "2026年4月14日",
                    str(output_dir),
                    "新检查员",
                )

                process_documents.assert_called_once_with(
                    str(big_path),
                    str(small_path),
                    [{"variety": "白菜", "rate": "6.150%"}],
                    "2026年4月14日",
                    str(output_dir),
                    "新检查员",
                )
                update_config.assert_called_once_with({"inspector_name": "新检查员"})
                self.assertTrue(result["success"])
                self.assertEqual(result["data_count"], 1)

    def test_execute_task_skips_config_update_when_inspector_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            big_path = root / "big.docx"
            small_path = root / "small.docx"
            big_path.write_text("big", encoding="utf-8")
            small_path.write_text("small", encoding="utf-8")
            output_dir = root / "output"
            output_dir.mkdir()

            with patch("backend.services.pesticide_service.get_config") as get_config, patch(
                "backend.services.pesticide_service.update_config"
            ) as update_config, patch(
                "backend.services.pesticide_service.process_documents"
            ):
                get_config.return_value = {"inspector_name": "检查员"}
                service = PesticideService()

                service.execute_task(
                    str(big_path),
                    str(small_path),
                    json.dumps([{"variety": "白菜", "rate": "6.150%"}], ensure_ascii=False),
                    "2026年4月14日",
                    str(output_dir),
                    "检查员",
                )

                update_config.assert_not_called()

    def test_find_target_files_returns_expected_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            big_dir = root / "big"
            small_dir = root / "small"
            big_dir.mkdir()
            small_dir.mkdir()
            (big_dir / "农残检测记录表2026.04.14.docx").write_text("big", encoding="utf-8")
            (small_dir / "单位农残记录表04.14.docx").write_text("small", encoding="utf-8")

            with patch("backend.services.pesticide_service.get_config", return_value={}):
                service = PesticideService()
                result = service.find_target_files(str(big_dir), str(small_dir), "2026", "04", "14")

            self.assertTrue(result["big_exists"])
            self.assertTrue(result["small_exists"])
            self.assertTrue(result["big_file"].endswith("农残检测记录表2026.04.14.docx"))
            self.assertTrue(result["small_file"].endswith("单位农残记录表04.14.docx"))


if __name__ == "__main__":
    unittest.main()
