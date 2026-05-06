import os
import unittest
from unittest.mock import patch

from backend.services.asr_provider import AsrProviderDiagnostics, AsrProviderError, AsrTranscriptionResult
from backend.services.daily_intake_asr_service import DailyIntakeAsrError, DailyIntakeAsrService


class FakeProvider:
    def __init__(self, provider: str, outcomes):
        self.provider = provider
        self.model = f"{provider}-model"
        self.outcomes = list(outcomes)
        self.calls = 0

    def provider_name(self):
        return self.provider

    def is_configured(self):
        return True

    def readiness_message(self):
        return f"{self.provider} ready"

    def diagnostics(self, *, probe_runtime: bool = False):
        return AsrProviderDiagnostics(
            provider=self.provider,
            model=self.model,
            dependency_available=True,
            configured=True,
            model_loaded=probe_runtime,
            requested_device="auto",
            device="cpu",
            timeout_seconds=1,
            message=f"{self.provider} diagnostics",
        )

    def transcribe_audio_for_provider(self, *, file_bytes: bytes, filename: str, content_type: str | None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeDailyIntakeParser:
    def parse_transcript(self, *, transcript: str, intake_date: str, category: str | None = None):
        if "invalid" in transcript:
            return {
                "success": False,
                "message": "无法解析",
                "raw_transcript": transcript,
                "parse_status": "invalid",
                "warnings": ["无法解析"],
                "requires_confirmation": True,
                "merge_preview": None,
            }
        return {
            "success": True,
            "message": "已解析",
            "raw_transcript": transcript,
            "draft_name": "土豆",
            "normalized_name": "土豆",
            "quantity": 3,
            "unit": "斤",
            "category_hint": category or "vegetable",
            "parse_status": "parsed",
            "warnings": [],
            "requires_confirmation": True,
            "merge_preview": None,
        }


class FakeShadowStore:
    def __init__(self):
        self.records = []

    def append(self, record):
        self.records.append(record)


def result(provider: str, transcript: str, quality_status: str = "ok", duration_ms: int = 12):
    return AsrTranscriptionResult(
        transcript=transcript,
        provider=provider,
        model=f"{provider}-model",
        quality_status=quality_status,
        duration_ms=duration_ms,
    )


class DailyIntakeAsrServiceTests(unittest.TestCase):
    def create_service(self, qwen_outcomes, whisper_outcomes, *, shadow=False):
        env = {
            "DAILY_INTAKE_ASR_PRIMARY": "qwen3-asr",
            "DAILY_INTAKE_ASR_BACKUP": "faster-whisper",
            "DAILY_INTAKE_ASR_FAILOVER": "true",
            "DAILY_INTAKE_ASR_SHADOW_COMPARE": "true" if shadow else "false",
        }
        patcher = patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        shadow_store = FakeShadowStore()
        service = DailyIntakeAsrService(
            qwen_provider=FakeProvider("qwen3-asr", qwen_outcomes),
            whisper_provider=FakeProvider("faster-whisper", whisper_outcomes),
            daily_intake_service=FakeDailyIntakeParser(),
            shadow_store=shadow_store,
        )
        return service, shadow_store

    def test_qwen_primary_success_does_not_fallback(self):
        service, _ = self.create_service(
            [result("qwen3-asr", "土豆3斤")],
            [result("faster-whisper", "土豆3斤")],
        )

        payload = service.transcribe_audio(
            file_bytes=b"audio",
            filename="clip.webm",
            content_type="audio/webm",
            intake_date="2026-04-25",
            asr_provider="auto",
        )

        self.assertEqual(payload["asr_provider"], "qwen3-asr")
        self.assertFalse(payload["asr_fallback_used"])
        self.assertEqual(service.providers["qwen3-asr"].calls, 1)
        self.assertEqual(service.providers["faster-whisper"].calls, 0)

    def test_qwen_failure_falls_back_to_whisper(self):
        service, _ = self.create_service(
            [AsrProviderError("qwen failed")],
            [result("faster-whisper", "土豆3斤")],
        )

        payload = service.transcribe_audio(
            file_bytes=b"audio",
            filename="clip.webm",
            content_type="audio/webm",
            intake_date="2026-04-25",
            asr_provider="auto",
        )

        self.assertEqual(payload["asr_provider"], "faster-whisper")
        self.assertTrue(payload["asr_fallback_used"])
        self.assertIn("qwen failed", payload["asr_fallback_reason"])

    def test_low_quality_qwen_falls_back_to_whisper(self):
        service, _ = self.create_service(
            [result("qwen3-asr", "土豆3斤", quality_status="low_quality")],
            [result("faster-whisper", "土豆3斤")],
        )

        payload = service.transcribe_audio(
            file_bytes=b"audio",
            filename="clip.webm",
            content_type="audio/webm",
            intake_date="2026-04-25",
            asr_provider="auto",
        )

        self.assertEqual(payload["asr_provider"], "faster-whisper")
        self.assertTrue(payload["asr_fallback_used"])
        self.assertIn("质量不达标", payload["asr_fallback_reason"])

    def test_double_failure_returns_stable_error(self):
        service, _ = self.create_service(
            [AsrProviderError("qwen failed")],
            [AsrProviderError("whisper failed")],
        )

        with self.assertRaises(DailyIntakeAsrError) as exc:
            service.transcribe_audio(
                file_bytes=b"audio",
                filename="clip.webm",
                content_type="audio/webm",
                intake_date="2026-04-25",
                asr_provider="auto",
            )

        self.assertIn("所有语音识别模型都失败", str(exc.exception))
        self.assertIn("qwen failed", str(exc.exception))
        self.assertIn("whisper failed", str(exc.exception))

    def test_shadow_compare_records_both_providers_without_changing_final_provider(self):
        service, shadow_store = self.create_service(
            [result("qwen3-asr", "土豆3斤")],
            [result("faster-whisper", "土豆3斤")],
            shadow=True,
        )

        payload = service.transcribe_audio(
            file_bytes=b"audio",
            filename="clip.webm",
            content_type="audio/webm",
            intake_date="2026-04-25",
            asr_provider="auto",
        )

        self.assertEqual(payload["asr_provider"], "qwen3-asr")
        self.assertEqual(service.providers["qwen3-asr"].calls, 1)
        self.assertEqual(service.providers["faster-whisper"].calls, 1)
        self.assertEqual(len(shadow_store.records), 1)
        self.assertEqual(shadow_store.records[0].final_provider, "qwen3-asr")
        self.assertEqual(shadow_store.records[0].primary_transcript, "土豆3斤")
        self.assertEqual(shadow_store.records[0].backup_transcript, "土豆3斤")


if __name__ == "__main__":
    unittest.main()
