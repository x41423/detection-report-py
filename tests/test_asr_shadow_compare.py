import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services.asr_shadow_compare import AsrShadowCompareStore


class AsrShadowCompareStoreTests(unittest.TestCase):
    def test_read_recent_returns_newest_valid_records(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "shadow.jsonl"
            store = AsrShadowCompareStore(path)
            store.append({"request_id": "old", "final_provider": "faster-whisper"})
            path.write_text(
                path.read_text(encoding="utf-8") + "not-json\n",
                encoding="utf-8",
            )
            store.append({"request_id": "new", "final_provider": "qwen3-asr"})

            records = store.read_recent(limit=2)

        self.assertEqual([record["request_id"] for record in records], ["new", "old"])

    def test_export_path_creates_empty_jsonl_file(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "nested" / "shadow.jsonl"
            store = AsrShadowCompareStore(path)

            export_path = store.export_path()

            self.assertEqual(export_path, path)
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
