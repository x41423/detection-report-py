import os
import time
import unittest
from unittest.mock import patch

from backend.services.asr_provider import AsrProviderTimeoutError, AsrTranscriptionResult
from backend.services.qwen3_asr_provider import QWEN_ASR_MODEL_TAG, Qwen3AsrProvider


class FakeProcessor:
    def apply_chat_template(self, messages, add_generation_prompt: bool, tokenize: bool):
        return f"{messages[0]['content']}|prompt|"


class Qwen3AsrProviderTests(unittest.TestCase):
    def create_provider(self, **env):
        base_env = {
            "DAILY_INTAKE_QWEN3_ASR_MODEL": "Qwen/Qwen3-ASR-1.7B",
            "DAILY_INTAKE_QWEN3_ASR_DEVICE": "auto",
            "DAILY_INTAKE_QWEN3_ASR_TIMEOUT_SECONDS": "1",
        }
        base_env.update(env)
        with patch.dict(os.environ, base_env, clear=False):
            return Qwen3AsrProvider()

    def test_build_qwen_prompt_adds_language_marker(self):
        provider = self.create_provider()

        prompt = provider._build_qwen_prompt(
            processor=FakeProcessor(),
            language="Chinese",
            context_prompt="Known correction pairs: 豆付 -> 豆腐 (板).",
        )

        self.assertIn("Known correction pairs", prompt)
        self.assertIn(f"language Chinese{QWEN_ASR_MODEL_TAG}", prompt)

    def test_diagnostics_without_probe_does_not_load_model(self):
        provider = self.create_provider()

        with (
            patch.object(provider, "is_dependency_available", return_value=True),
            patch.object(provider, "_resolve_device", return_value="cpu"),
            patch.object(provider, "_get_or_create_model") as get_model,
        ):
            diagnostics = provider.diagnostics(probe_runtime=False)

        self.assertTrue(diagnostics.dependency_available)
        self.assertFalse(diagnostics.model_loaded)
        get_model.assert_not_called()

    def test_diagnostics_reports_missing_dependencies(self):
        provider = self.create_provider()

        def fake_distribution_version(package_name):
            return None if package_name == "qwen-asr" else "1.0"

        def fake_find_spec(module_name):
            return None if module_name in {"transformers", "accelerate"} else object()

        with (
            patch.object(provider, "_get_distribution_version", side_effect=fake_distribution_version),
            patch.object(provider, "_get_module_version", return_value="1.0"),
            patch("backend.services.qwen3_asr_provider.importlib.util.find_spec", side_effect=fake_find_spec),
        ):
            diagnostics = provider.diagnostics(probe_runtime=False)

        self.assertFalse(diagnostics.dependency_available)
        self.assertEqual(
            diagnostics.raw["missing_dependencies"],
            ["qwen-asr", "transformers", "accelerate"],
        )
        self.assertIn("py -3 -m pip install -r backend/requirements.txt", diagnostics.raw["suggested_fix"])

    def test_readiness_message_names_missing_dependencies(self):
        provider = self.create_provider()

        def fake_find_spec(module_name):
            return None if module_name == "transformers" else object()

        with (
            patch.object(provider, "_get_distribution_version", return_value="1.0"),
            patch("backend.services.qwen3_asr_provider.importlib.util.find_spec", side_effect=fake_find_spec),
        ):
            message = provider.readiness_message()

        self.assertIn("Qwen3-ASR 依赖未就绪", message)
        self.assertIn("缺少：transformers", message)
        self.assertIn("faster-whisper", message)

    def test_transcribe_timeout_raises_provider_timeout(self):
        provider = self.create_provider(DAILY_INTAKE_QWEN3_ASR_TIMEOUT_SECONDS="0.01")

        def slow_operation(*, file_bytes, filename, content_type):
            time.sleep(0.05)
            raise AssertionError("operation should time out first")

        with patch.object(provider, "_transcribe_audio_once", side_effect=slow_operation):
            with self.assertRaises(AsrProviderTimeoutError):
                provider.transcribe_audio_for_provider(
                    file_bytes=b"audio",
                    filename="clip.webm",
                    content_type="audio/webm",
                )

    def test_transcribe_with_options_passes_lab_overrides(self):
        provider = self.create_provider()
        expected = AsrTranscriptionResult(
            transcript="白菜三斤",
            provider="qwen3-asr",
            model="Qwen/Qwen3-ASR-0.6B",
        )

        with (
            patch.object(provider, "_run_with_timeout", side_effect=lambda operation, timeout_seconds: operation()) as run,
            patch.object(provider, "_transcribe_audio_once", return_value=expected) as transcribe_once,
        ):
            result = provider.transcribe_audio_with_options(
                file_bytes=b"audio",
                filename="clip.webm",
                content_type="audio/webm",
                model="Qwen/Qwen3-ASR-0.6B",
                device="cpu",
                language="Chinese",
                max_new_tokens=128,
                extra_context="temporary context",
                use_domain_context=False,
                context_prompt_override="lab prompt",
                timeout_seconds=3,
            )

        self.assertIs(result, expected)
        self.assertEqual(run.call_args.kwargs["timeout_seconds"], 3)
        kwargs = transcribe_once.call_args.kwargs
        self.assertEqual(kwargs["model"], "Qwen/Qwen3-ASR-0.6B")
        self.assertEqual(kwargs["device"], "cpu")
        self.assertEqual(kwargs["language"], "Chinese")
        self.assertEqual(kwargs["max_new_tokens"], 128)
        self.assertFalse(kwargs["use_domain_context"])
        self.assertEqual(kwargs["context_prompt_override"], "lab prompt")

    def test_parse_qwen_output_strips_marker_with_forced_language(self):
        provider = self.create_provider()

        language, transcript = provider._parse_qwen_output(
            f"language Chinese{QWEN_ASR_MODEL_TAG}白菜三斤",
            forced_language="Chinese",
        )

        self.assertEqual(language, "Chinese")
        self.assertEqual(transcript, "白菜三斤")


if __name__ == "__main__":
    unittest.main()
