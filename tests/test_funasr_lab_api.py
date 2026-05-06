import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class FunASRLabApiTests(unittest.TestCase):
    def setUp(self):
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)

    def test_funasr_lab_page_is_served(self):
        response = self.client.get("/tests/funasr-lab")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Qwen3-ASR 1.7B 测试页", response.text)

    def test_funasr_lab_status_endpoint(self):
        response = self.client.get("/api/test/funasr-lab/status")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["provider"], "qwen3-asr")
        self.assertIn("defaults", body)

    def test_funasr_lab_tracking_endpoint(self):
        mocked_payload = {
            "success": True,
            "selected_day": {
                "intake_date": "2026-04-21",
                "total_count": 3,
                "merge_event_count": 4,
                "unique_name_count": 3,
                "total_quantity": 9.5,
                "items": [],
            },
            "recent_days": [],
        }

        with patch(
            "backend.funasr_lab.router.service.tracking_status",
            return_value=mocked_payload,
        ) as mocked_tracking_status:
            response = self.client.get("/api/test/funasr-lab/tracking?intake_date=2026-04-21&days=7")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["selected_day"]["total_count"], 3)
        mocked_tracking_status.assert_called_once_with(intake_date="2026-04-21", days=7)

    def test_funasr_lab_tracking_record_endpoint(self):
        mocked_payload = {
            "success": True,
            "merged": False,
            "message": "Added to today's tracking.",
            "selected_day": {"intake_date": "2026-04-21", "total_count": 1, "items": []},
            "recent_days": [],
        }

        with patch(
            "backend.funasr_lab.router.service.record_tracking_entry",
            return_value=mocked_payload,
        ) as mocked_record_tracking:
            response = self.client.post(
                "/api/test/funasr-lab/tracking/record",
                json={
                    "intake_date": "2026-04-21",
                    "raw_name": "\u5c0f\u571f\u8c46",
                    "normalized_name": "\u571f\u8c46",
                    "unit": "\u65a4",
                    "quantity": 2,
                    "category": "vegetable",
                    "transcript": "\u571f\u8c46\u4e24\u65a4",
                    "source": "funasr-lab",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Added to today's tracking.")
        mocked_record_tracking.assert_called_once()

    def test_funasr_lab_lexicon_endpoint(self):
        mocked_payload = {
            "success": True,
            "lexicon_version": 2,
            "counts": {"pending": 1, "confirmed": 0, "active": 3, "disabled": 0, "exported": 0},
            "entries": [],
        }

        with patch(
            "backend.funasr_lab.router.service.lexicon_status",
            return_value=mocked_payload,
        ) as mocked_lexicon_status:
            response = self.client.get("/api/test/funasr-lab/lexicon")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["lexicon_version"], 2)
        mocked_lexicon_status.assert_called_once_with(include_entries=True)

    def test_funasr_lab_lexicon_confirm_and_apply_endpoints(self):
        with patch(
            "backend.funasr_lab.router.service.confirm_lexicon_entries",
            return_value={"success": True, "confirmed_total": 1, "lexicon_version": 0},
        ) as mocked_confirm:
            confirm_response = self.client.post(
                "/api/test/funasr-lab/lexicon/confirm",
                json={"ids": ["abc"]},
            )

        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.json()["confirmed_total"], 1)
        mocked_confirm.assert_called_once_with(ids=["abc"])

        with patch(
            "backend.funasr_lab.router.service.apply_incremental_lexicon",
            return_value={
                "success": True,
                "lexicon_version": 1,
                "activated_total": 1,
                "effective_pair_total": 1,
                "message": "applied",
            },
        ) as mocked_apply:
            apply_response = self.client.post(
                "/api/test/funasr-lab/lexicon/apply-incremental",
                json={"scope": "all_confirmed"},
            )

        self.assertEqual(apply_response.status_code, 200)
        self.assertEqual(apply_response.json()["activated_total"], 1)
        mocked_apply.assert_called_once_with(scope="all_confirmed", ids=None)

    def test_funasr_lab_lexicon_export_training_pack_endpoint(self):
        with patch(
            "backend.funasr_lab.router.service.export_lexicon_training_pack",
            return_value={
                "success": True,
                "exported_total": 2,
                "filename": "qwen3-asr-corrections-20260424-135500.jsonl",
                "message": "Exported text-only correction training pack. No audio paths were included.",
            },
        ) as mocked_export:
            response = self.client.post(
                "/api/test/funasr-lab/lexicon/export-training-pack",
                json={"statuses": ["confirmed", "active"]},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["exported_total"], 2)
        mocked_export.assert_called_once_with(statuses=["confirmed", "active"], ids=None)

    def test_funasr_lab_transcribe_uses_qwen_service(self):
        mocked_payload = {
            "success": True,
            "asr": {
                "provider": "qwen3-asr",
                "model": "Qwen/Qwen3-ASR-1.7B",
                "transcript": "\u767d\u83dc\u56db\u65a4",
                "language": "Chinese",
            },
            "baseline": None,
            "daily_intake_parse": None,
            "config": {"model": "Qwen/Qwen3-ASR-1.7B"},
        }

        with patch(
            "backend.funasr_lab.router.service.transcribe_audio",
            return_value=mocked_payload,
        ) as mocked_transcribe:
            response = self.client.post(
                "/api/test/funasr-lab/transcribe",
                files={"audio": ("lab.wav", b"test-audio", "audio/wav")},
                data={
                    "model": "Qwen/Qwen3-ASR-1.7B",
                    "language": "Chinese",
                    "max_new_tokens": "256",
                    "use_domain_context": "true",
                    "extra_context": "Supplier A only",
                    "compare_with_baseline": "false",
                    "parse_daily_intake": "false",
                    "retain_training_audio": "true",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["asr"]["provider"], "qwen3-asr")
        mocked_transcribe.assert_called_once()
        call_config = mocked_transcribe.call_args.kwargs["config"]
        self.assertTrue(call_config.use_domain_context)
        self.assertEqual(call_config.extra_context, "Supplier A only")
        self.assertTrue(call_config.retain_training_audio)


if __name__ == "__main__":
    unittest.main()
