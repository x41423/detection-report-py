import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.asr_correction_lexicon import AsrCorrectionEntry
from backend.services.speech_to_text_service import (
    SpeechToTextDiagnostics,
    SpeechToTextConfigError,
    SpeechToTextService,
    SpeechToTextRuntimeStatus,
)


class SpeechToTextServiceTests(unittest.TestCase):
    def create_service(self, **env_overrides):
        base_env = {
            "DAILY_INTAKE_STT_DEVICE": "auto",
            "DAILY_INTAKE_STT_COMPUTE_TYPE": "auto",
            "DAILY_INTAKE_STT_MODEL": "medium",
            "DAILY_INTAKE_STT_LANGUAGE": "zh",
        }
        base_env.update(env_overrides)
        with patch.dict(os.environ, base_env, clear=False):
            return SpeechToTextService()

    def test_auto_prefers_cuda_float16_when_available(self):
        service = self.create_service()

        with (
            patch.object(service, "_get_cuda_device_count", return_value=1),
            patch.object(service, "_get_supported_compute_types", return_value={"float16", "int8_float16", "int8"}),
        ):
            status = service.runtime_status()

        self.assertEqual(status.requested_device, "auto")
        self.assertEqual(status.requested_compute_type, "auto")
        self.assertEqual(status.device, "cuda")
        self.assertEqual(status.compute_type, "float16")
        self.assertFalse(status.fallback_used)

    def test_explicit_cuda_raises_when_no_gpu_available(self):
        service = self.create_service(
            DAILY_INTAKE_STT_DEVICE="cuda",
            DAILY_INTAKE_STT_COMPUTE_TYPE="float16",
        )

        with patch.object(service, "_get_cuda_device_count", return_value=0):
            with self.assertRaises(SpeechToTextConfigError):
                service.runtime_status()

    def test_gpu_init_failure_falls_back_to_cpu_for_auto_mode(self):
        service = self.create_service()

        def supported_compute_types(device: str) -> set[str]:
            return {"float16", "int8_float16"} if device == "cuda" else {"int8", "float32"}

        def create_model(_, *, device: str, compute_type: str):
            if device == "cuda":
                raise RuntimeError("mock gpu init failed")
            return object()

        with (
            patch.object(service, "_get_cuda_device_count", return_value=1),
            patch.object(service, "_get_supported_compute_types", side_effect=supported_compute_types),
            patch.object(service, "_create_whisper_model", side_effect=create_model),
        ):
            model = service._get_model_instance()
            status = service.runtime_status()

        self.assertIsNotNone(model)
        self.assertEqual(status.device, "cpu")
        self.assertEqual(status.compute_type, "int8")
        self.assertTrue(status.fallback_used)
        self.assertIn("GPU", status.fallback_reason or "")

    def test_gpu_runtime_probe_failure_falls_back_to_cpu_for_auto_mode(self):
        service = self.create_service()
        gpu_model = object()
        cpu_model = object()

        def supported_compute_types(device: str) -> set[str]:
            return {"float16", "int8_float16"} if device == "cuda" else {"int8", "float32"}

        def create_model(_, *, device: str, compute_type: str):
            return gpu_model if device == "cuda" else cpu_model

        def probe_model_runtime(model, status):
            if model is gpu_model:
                raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")

        with (
            patch.object(service, "_get_cuda_device_count", return_value=1),
            patch.object(service, "_get_supported_compute_types", side_effect=supported_compute_types),
            patch.object(service, "_create_whisper_model", side_effect=create_model),
            patch.object(service, "_probe_model_runtime", side_effect=probe_model_runtime),
        ):
            model = service._get_model_instance()
            status = service.runtime_status()

        self.assertIs(model, cpu_model)
        self.assertEqual(status.device, "cpu")
        self.assertEqual(status.compute_type, "int8")
        self.assertTrue(status.fallback_used)
        self.assertIn("cublas64_12.dll", status.fallback_reason or "")

    def test_diagnostics_without_probe_reports_resolved_runtime(self):
        service = self.create_service()

        def supported_compute_types(device: str) -> set[str]:
            return {"float16", "int8_float16"} if device == "cuda" else {"int8", "float32"}

        with (
            patch.object(service, "is_dependency_available", return_value=True),
            patch.object(service, "_get_cuda_device_count", return_value=1),
            patch.object(service, "_get_supported_compute_types", side_effect=supported_compute_types),
            patch.object(service, "_get_missing_cuda_runtime_dlls", return_value=["cublas64_12.dll"]),
        ):
            diagnostics = service.diagnostics()

        self.assertIsInstance(diagnostics, SpeechToTextDiagnostics)
        self.assertEqual(diagnostics.resolved_device, "cuda")
        self.assertEqual(diagnostics.resolved_compute_type, "float16")
        self.assertIsNone(diagnostics.effective_device)
        self.assertFalse(diagnostics.runtime_checked)
        self.assertEqual(diagnostics.cuda_device_count, 1)
        self.assertEqual(diagnostics.supported_compute_types_cpu, ["float32", "int8"])
        self.assertEqual(diagnostics.supported_compute_types_cuda, ["float16", "int8_float16"])
        self.assertEqual(diagnostics.missing_cuda_runtime_dlls, ["cublas64_12.dll"])
        self.assertIn("CUDA 12", diagnostics.suggested_fix or "")

    def test_diagnostics_with_probe_reports_actual_runtime_after_fallback(self):
        service = self.create_service()

        resolved_status = SpeechToTextRuntimeStatus(
            requested_device="auto",
            requested_compute_type="auto",
            device="cuda",
            compute_type="float16",
            fallback_used=False,
            fallback_reason=None,
        )

        def supported_compute_types(device: str) -> set[str]:
            return {"float16", "int8_float16"} if device == "cuda" else {"int8", "float32"}

        def warmup_model():
            service._model_instance = object()
            service._apply_runtime_status(
                SpeechToTextRuntimeStatus(
                    requested_device="auto",
                    requested_compute_type="auto",
                    device="cpu",
                    compute_type="int8",
                    fallback_used=True,
                    fallback_reason="GPU runtime unavailable",
                )
            )
            return "ok"

        with (
            patch.object(service, "is_dependency_available", return_value=True),
            patch.object(service, "_get_cuda_device_count", return_value=1),
            patch.object(service, "_get_supported_compute_types", side_effect=supported_compute_types),
            patch.object(service, "_get_missing_cuda_runtime_dlls", return_value=["cublas64_12.dll"]),
            patch.object(service, "_resolve_runtime_status", return_value=resolved_status),
            patch.object(service, "warmup_model", side_effect=warmup_model),
        ):
            diagnostics = service.diagnostics(probe_runtime=True)

        self.assertTrue(diagnostics.runtime_checked)
        self.assertTrue(diagnostics.model_loaded)
        self.assertEqual(diagnostics.resolved_device, "cuda")
        self.assertEqual(diagnostics.resolved_compute_type, "float16")
        self.assertEqual(diagnostics.effective_device, "cpu")
        self.assertEqual(diagnostics.effective_compute_type, "int8")
        self.assertTrue(diagnostics.fallback_used)
        self.assertEqual(diagnostics.fallback_reason, "GPU runtime unavailable")
        self.assertEqual(diagnostics.missing_cuda_runtime_dlls, ["cublas64_12.dll"])

    def test_context_bias_mentions_noise_and_decimal_examples(self):
        service = self.create_service()

        with patch.object(service, "_collect_domain_vocabulary", return_value=["大白菜", "鸡腿"]):
            initial_prompt, hotwords = service._build_context_bias()

        self.assertIn("背景噪声", initial_prompt)
        self.assertIn("距离麦克风最近的人声", initial_prompt)
        self.assertIn("阿拉伯数字", initial_prompt)
        self.assertIn("小数点", initial_prompt)
        self.assertIn("4.8斤", initial_prompt)
        self.assertIn("4斤8斤", initial_prompt)
        self.assertEqual(hotwords, "大白菜,鸡腿")

    def test_context_bias_uses_active_asr_correction_lexicon(self):
        service = self.create_service()
        entries = [
            AsrCorrectionEntry(
                alias="豆付",
                canonical_name="豆腐",
                unit="板",
                status="active",
                use_count=3,
            )
        ]

        with (
            patch.object(service, "_load_active_correction_entries", return_value=entries),
            patch("backend.services.speech_to_text_service.VegRepository.get_all_vegetables", return_value=[]),
            patch("backend.services.speech_to_text_service.load_config", return_value={}),
        ):
            initial_prompt, hotwords = service._build_context_bias()

        self.assertIn("豆付应识别为豆腐", initial_prompt)
        self.assertIn("豆付", hotwords or "")
        self.assertIn("豆腐", hotwords or "")
        self.assertIn("板", hotwords or "")

    def test_context_bias_can_disable_asr_correction_lexicon(self):
        service = self.create_service(DAILY_INTAKE_STT_USE_ASR_CORRECTIONS="false")

        with patch.object(service.correction_lexicon, "load_entries") as mocked_load_entries:
            service._build_context_bias()

        mocked_load_entries.assert_not_called()

    def test_fit_context_bias_trims_combined_prompt_to_model_budget(self):
        service = self.create_service()

        class FakeTokenizer:
            sot_sequence = [1, 2, 3]

            def encode(self, text: str):
                return list(text.strip())

        class FakeModel:
            max_length = 24

        with patch.object(service, "_create_context_tokenizer", return_value=FakeTokenizer()):
            initial_prompt, hotwords = service._fit_context_bias_to_model(
                FakeModel(),
                initial_prompt="abcdefghij",
                hotwords="one,two,three",
            )

        self.assertEqual(len(initial_prompt or []), 10)
        self.assertEqual(hotwords, "one")

    def test_configure_windows_dll_directories_uses_existing_relative_env_paths(self):
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as temp_dir:
            dll_dir = os.path.join(temp_dir, "runtime", "bin")
            os.makedirs(dll_dir, exist_ok=True)

            with (
                patch.dict(
                    os.environ,
                    {"DAILY_INTAKE_STT_DLL_DIRS": os.path.relpath(dll_dir, os.getcwd())},
                    clear=False,
                ),
                patch("backend.services.speech_to_text_service.ROOT_DIR", Path(os.getcwd())),
                patch("backend.services.speech_to_text_service.os.name", "nt"),
                patch("backend.services.speech_to_text_service.os.add_dll_directory") as add_dll_directory,
            ):
                self.create_service()

            configured_paths = [call.args[0] for call in add_dll_directory.call_args_list]
            self.assertTrue(
                any(path.endswith(os.path.join("runtime", "bin")) for path in configured_paths)
            )


if __name__ == "__main__":
    unittest.main()
