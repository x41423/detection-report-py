import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend.services.asr_correction_lexicon import AsrCorrectionLexicon


class AsrCorrectionLexiconTests(unittest.TestCase):
    def test_load_entries_returns_active_entries_only(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "funasr_lab_corrections.json"
            path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "alias": "\u8c46\u4ed8",
                                "canonical_name": "\u8c46\u8150",
                                "unit": "\u677f",
                                "status": "active",
                                "use_count": 5,
                            },
                            {
                                "alias": "\u9752\u7126",
                                "canonical_name": "\u9752\u6912",
                                "unit": "\u65a4",
                                "status": "pending",
                                "use_count": 10,
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            entries = AsrCorrectionLexicon(path).load_entries()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].alias, "\u8c46\u4ed8")
        self.assertEqual(entries[0].canonical_name, "\u8c46\u8150")


if __name__ == "__main__":
    unittest.main()
