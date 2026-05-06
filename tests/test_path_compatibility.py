import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.db.store import resolve_default_db_path
from app.models import config_model
from shared.pesticide_data import DataGeneratorService
from shared.project_paths import ProjectPaths


class ConfigCompatibilityTests(unittest.TestCase):
    def test_load_config_reads_legacy_file_and_writes_canonical_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ProjectPaths.for_root(Path(tmpdir))
            paths.legacy_root_config_file.write_text(
                json.dumps({"inspector_name": "legacy-user"}, ensure_ascii=False),
                encoding="utf-8",
            )

            with patch("app.models.config_model.get_project_paths", return_value=paths):
                config = config_model.load_config()

            self.assertEqual(config["inspector_name"], "legacy-user")
            self.assertTrue(paths.config_file.exists())
            stored = json.loads(paths.config_file.read_text(encoding="utf-8"))
            self.assertEqual(stored["inspector_name"], "legacy-user")


class HistoryCompatibilityTests(unittest.TestCase):
    def test_history_falls_back_to_legacy_file_and_saves_to_canonical_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ProjectPaths.for_root(Path(tmpdir))
            paths.legacy_history_rates_file.write_text(
                json.dumps(
                    {
                        "high": [],
                        "low": [],
                        "other": [],
                        "variety_rates": {"白菜": 1.23},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch("shared.pesticide_data.get_project_paths", return_value=paths):
                service = DataGeneratorService(history_file=paths.history_rates_file)
                loaded = service.load_history()
                service.save_history(loaded)

            self.assertEqual(loaded["variety_rates"]["白菜"], 1.23)
            self.assertTrue(paths.history_rates_file.exists())
            stored = json.loads(paths.history_rates_file.read_text(encoding="utf-8"))
            self.assertEqual(stored["variety_rates"]["白菜"], 1.23)


class DatabaseCompatibilityTests(unittest.TestCase):
    def test_resolve_default_db_path_copies_legacy_database_to_canonical_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = ProjectPaths.for_root(Path(tmpdir))
            paths.legacy_database_file.parent.mkdir(parents=True, exist_ok=True)
            paths.legacy_database_file.write_bytes(b"legacy-db")

            resolved = resolve_default_db_path(paths)

            self.assertEqual(resolved, paths.database_file)
            self.assertTrue(paths.database_file.exists())
            self.assertEqual(paths.database_file.read_bytes(), b"legacy-db")


if __name__ == "__main__":
    unittest.main()
