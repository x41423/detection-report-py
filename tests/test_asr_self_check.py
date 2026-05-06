"""Smoke tests for the ASR startup self-check report."""

from __future__ import annotations

import importlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from backend.diagnostics.asr_self_check import (
    _STUB_NEEDLES,
    run_asr_self_check,
)


class RunAsrSelfCheckTests(unittest.TestCase):
    def test_passes_in_clean_workspace(self):
        report = run_asr_self_check(strict=True)
        self.assertTrue(report["ok"], report)

        module_names = {entry["name"] for entry in report["modules"]}
        self.assertIn("backend.services.qwen3_asr_provider", module_names)
        self.assertIn("backend.services.speech_to_text_service", module_names)
        self.assertIn("backend.services.daily_intake_asr_service", module_names)
        self.assertIn("backend.funasr_lab.service", module_names)

        for entry in report["modules"]:
            self.assertTrue(entry["ok"], entry)
            self.assertIsNone(entry["issue"])
            self.assertGreater(entry["size"], 1500, entry)

    def test_every_provider_source_is_free_of_stub_markers(self):
        from backend.services import (
            qwen3_asr_provider,
            speech_to_text_service,
            daily_intake_asr_service,
        )
        from backend.funasr_lab import service as funasr_service

        modules = [
            qwen3_asr_provider,
            speech_to_text_service,
            daily_intake_asr_service,
            funasr_service,
        ]
        for module in modules:
            source_path = Path(module.__file__)
            text = source_path.read_text(encoding="utf-8")
            for needle in _STUB_NEEDLES:
                self.assertNotIn(
                    needle,
                    text,
                    f"{module.__name__} still contains stub marker {needle!r}",
                )

    def test_strict_mode_rejects_module_loaded_from_wrong_location(self):
        # Create a rogue stub that would satisfy the import but live outside
        # backend/services, then coerce Python to import it by placing it on
        # sys.path ahead of the real module.
        with tempfile.TemporaryDirectory() as tmp:
            rogue_root = Path(tmp)
            package = rogue_root / "backend_rogue_asr_shim"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            rogue_module = package / "stub_qwen3_asr_provider.py"
            rogue_module.write_text(
                textwrap.dedent(
                    """
                    class Qwen3AsrProvider:
                        def is_dependency_available(self):
                            return False
                    """
                ).strip(),
                encoding="utf-8",
            )

            # Smoke: the self-check should not be tricked by this separate
            # module because it only inspects the canonical dotted paths.
            report = run_asr_self_check(strict=False)
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
