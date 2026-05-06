import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.db.store as store
from backend.api.routes import daily_intake as daily_intake_route
from backend.main import app


class DailyIntakeApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "daily-intake-api.db")
        store._connection = None
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)
        store.close_connection()
        store.DB_DIR = self.original_db_dir
        store.DB_PATH = self.original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def test_today_endpoint_creates_sheet(self):
        response = self.client.get("/api/daily-intake/today")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIn("sheet", body)
        self.assertIn("intake_date", body["sheet"])

    def test_item_endpoint_accumulates_duplicate_item(self):
        payload = {
            "intake_date": "2026-04-15",
            "name": "土豆",
            "category": "vegetable",
            "quantity": 5,
            "unit": "斤",
            "source": "manual",
            "transcript": "",
        }

        first = self.client.post("/api/daily-intake/items", json=payload)
        second = self.client.post(
            "/api/daily-intake/items",
            json={**payload, "quantity": 2, "source": "voice", "transcript": "土豆二斤"},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        body = second.json()
        self.assertTrue(body["merged"])
        self.assertEqual(body["sheet"]["item_count"], 1)
        self.assertEqual(body["sheet"]["items"][0]["quantity"], 7)
        self.assertEqual(body["sheet"]["items"][0]["last_source"], "voice")

    def test_parse_transcript_endpoint(self):
        response = self.client.post(
            "/api/daily-intake/parse-transcript",
            json={"intake_date": "2026-04-15", "transcript": "白菜三斤"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["parse_status"], "parsed")
        self.assertEqual(body["draft_name"], "白菜")
        self.assertEqual(body["unit"], "斤")

    def test_speech_capabilities_returns_runtime_status(self):
        with patch.object(
            daily_intake_route.speech_to_text_service,
            "capabilities",
            return_value={
                "success": True,
                "stable_transcription_enabled": True,
                "provider": "qwen3-asr",
                "model": "Qwen/Qwen3-ASR-1.7B",
                "requested_device": "auto",
                "requested_compute_type": None,
                "device": "cuda:0",
                "compute_type": None,
                "fallback_used": False,
                "fallback_reason": None,
                "primary_provider": "qwen3-asr",
                "backup_provider": "faster-whisper",
                "failover_enabled": True,
                "shadow_compare_enabled": True,
                "providers": [
                    {"provider": "qwen3-asr", "configured": True},
                    {"provider": "faster-whisper", "configured": True},
                ],
                "message": "ok",
            },
        ):
            response = self.client.get("/api/daily-intake/speech-capabilities")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["stable_transcription_enabled"])
        self.assertEqual(body["provider"], "qwen3-asr")
        self.assertEqual(body["primary_provider"], "qwen3-asr")
        self.assertEqual(body["backup_provider"], "faster-whisper")
        self.assertEqual(body["requested_device"], "auto")
        self.assertEqual(body["device"], "cuda:0")
        self.assertFalse(body["fallback_used"])
        self.assertEqual(len(body["providers"]), 2)

    def test_speech_runtime_diagnostics_returns_effective_runtime(self):
        with patch.object(
            daily_intake_route.speech_to_text_service,
            "diagnostics",
            return_value={
                "success": True,
                "dependency_available": True,
                "provider": "qwen3-asr",
                "model": "Qwen/Qwen3-ASR-1.7B",
                "requested_device": "auto",
                "requested_compute_type": None,
                "resolved_device": "cuda:0",
                "resolved_compute_type": None,
                "effective_device": "cuda:0",
                "effective_compute_type": None,
                "cuda_device_count": 1,
                "supported_compute_types_cpu": ["float32", "int8"],
                "supported_compute_types_cuda": ["float16", "int8_float16"],
                "missing_cuda_runtime_dlls": [],
                "model_loaded": True,
                "runtime_checked": True,
                "fallback_used": False,
                "fallback_reason": None,
                "suggested_fix": None,
                "primary_provider": "qwen3-asr",
                "backup_provider": "faster-whisper",
                "failover_enabled": True,
                "shadow_compare_enabled": True,
                "providers": [{"provider": "qwen3-asr", "model_loaded": True}],
                "message": "runtime checked",
            },
        ):
            response = self.client.get("/api/daily-intake/speech-runtime-diagnostics")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["dependency_available"])
        self.assertEqual(body["provider"], "qwen3-asr")
        self.assertEqual(body["resolved_device"], "cuda:0")
        self.assertEqual(body["effective_device"], "cuda:0")
        self.assertFalse(body["fallback_used"])
        self.assertEqual(body["primary_provider"], "qwen3-asr")
        self.assertEqual(body["backup_provider"], "faster-whisper")

    def test_transcribe_audio_passes_provider_selection_to_asr_service(self):
        with patch.object(
            daily_intake_route.speech_to_text_service,
            "transcribe_audio",
            return_value={
                "success": True,
                "message": "已解析",
                "raw_transcript": "土豆3斤",
                "draft_name": "土豆",
                "normalized_name": "土豆",
                "quantity": 3,
                "unit": "斤",
                "category_hint": "vegetable",
                "warnings": [],
                "parse_status": "parsed",
                "requires_confirmation": True,
                "merge_preview": None,
                "asr_provider": "qwen3-asr",
                "asr_model": "Qwen/Qwen3-ASR-1.7B",
                "asr_fallback_used": False,
                "asr_fallback_reason": None,
                "asr_duration_ms": 123,
                "asr_warnings": [],
                "asr_shadow_recorded": True,
            },
        ) as transcribe_audio:
            response = self.client.post(
                "/api/daily-intake/transcribe-audio",
                data={
                    "intake_date": "2026-04-25",
                    "category": "vegetable",
                    "asr_provider": "qwen3-asr",
                    "fallback_enabled": "true",
                },
                files={"audio": ("clip.webm", b"audio", "audio/webm")},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["asr_provider"], "qwen3-asr")
        self.assertEqual(body["asr_model"], "Qwen/Qwen3-ASR-1.7B")
        transcribe_audio.assert_called_once()
        self.assertEqual(transcribe_audio.call_args.kwargs["asr_provider"], "qwen3-asr")
        self.assertTrue(transcribe_audio.call_args.kwargs["fallback_enabled"])

    def test_asr_shadow_compare_endpoint_returns_recent_records(self):
        with patch.object(
            daily_intake_route.speech_to_text_service.shadow_store,
            "read_recent",
            return_value=[{"request_id": "r1", "final_provider": "qwen3-asr"}],
        ) as read_recent:
            response = self.client.get("/api/daily-intake/asr-shadow-compare?limit=1")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["total_returned"], 1)
        self.assertEqual(body["records"][0]["request_id"], "r1")
        read_recent.assert_called_once_with(limit=1)

    def test_asr_shadow_compare_export_returns_jsonl_file(self):
        shadow_path = os.path.join(self.temp_dir.name, "shadow.jsonl")
        with open(shadow_path, "w", encoding="utf-8") as handle:
            handle.write('{"request_id":"r1"}\n')

        with patch.object(
            daily_intake_route.speech_to_text_service.shadow_store,
            "export_path",
            return_value=Path(shadow_path),
        ):
            response = self.client.get("/api/daily-intake/asr-shadow-compare/export")

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-ndjson", response.headers["content-type"])
        self.assertIn('"request_id":"r1"', response.text)

    def test_history_editing_does_not_touch_today_sheet(self):
        self.client.post(
            "/api/daily-intake/items",
            json={
                "intake_date": "2026-04-14",
                "name": "白菜",
                "category": "vegetable",
                "quantity": 2,
                "unit": "斤",
                "source": "manual",
                "transcript": "",
            },
        )
        self.client.post(
            "/api/daily-intake/items",
            json={
                "intake_date": "2026-04-15",
                "name": "鸡腿",
                "category": "meat",
                "quantity": 1,
                "unit": "箱",
                "source": "manual",
                "transcript": "",
            },
        )

        yesterday = self.client.get("/api/daily-intake/2026-04-14")
        today = self.client.get("/api/daily-intake/2026-04-15")

        self.assertEqual(yesterday.status_code, 200)
        self.assertEqual(today.status_code, 200)
        self.assertEqual(yesterday.json()["sheet"]["items"][0]["raw_name"], "白菜")
        self.assertEqual(today.json()["sheet"]["items"][0]["raw_name"], "鸡腿")


if __name__ == "__main__":
    unittest.main()
