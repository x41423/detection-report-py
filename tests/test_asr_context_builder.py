import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.services.asr_context_builder import AsrContextBuilder
from backend.services.asr_correction_lexicon import AsrCorrectionLexicon


class AsrContextBuilderTests(unittest.TestCase):
    def test_only_active_corrections_enter_formal_contexts(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "funasr_lab_corrections.json"
            path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {"alias": "豆付", "canonical_name": "豆腐", "unit": "板", "status": "active"},
                            {"alias": "青焦", "canonical_name": "青椒", "unit": "斤", "status": "pending"},
                            {"alias": "茄纸", "canonical_name": "茄子", "unit": "斤", "status": "confirmed"},
                            {"alias": "白才", "canonical_name": "白菜", "unit": "斤", "status": "disabled"},
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            builder = AsrContextBuilder(lexicon=AsrCorrectionLexicon(path))

            with (
                patch("backend.services.asr_context_builder.VegRepository.get_all_vegetables", return_value=[]),
                patch("backend.services.asr_context_builder.load_config", return_value={}),
            ):
                whisper_context = builder.build_faster_whisper_context()
                qwen_context = builder.build_qwen_context()

        self.assertIn("豆付", whisper_context.initial_prompt)
        self.assertIn("豆付", whisper_context.hotwords or "")
        self.assertIn("豆付 -> 豆腐", qwen_context.system_prompt)
        for inactive in ("青焦", "茄纸", "白才"):
            self.assertNotIn(inactive, whisper_context.initial_prompt)
            self.assertNotIn(inactive, whisper_context.hotwords or "")
            self.assertNotIn(inactive, qwen_context.system_prompt)


if __name__ == "__main__":
    unittest.main()
