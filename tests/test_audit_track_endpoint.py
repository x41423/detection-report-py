"""Behavioural tests for the frontend audit track endpoint."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db import store
from backend.api.routes.audit import _reset_debounce_cache
from backend.main import app
from backend.services.audit_log_service import AuditLogService


class AuditTrackEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._original_db_dir = store.DB_DIR
        self._original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "audit-track.db")
        store._connection = None

        self.env_patch = patch.dict(
            os.environ,
            {
                "SEED_SUPER_ADMIN_USERNAME": "track.admin",
                "SEED_SUPER_ADMIN_PASSWORD": "track-password",
                "SEED_SUPER_ADMIN_FORCE_CHANGE_PASSWORD": "false",
            },
            clear=False,
        )
        self.env_patch.start()

        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()
        self.audit_service = AuditLogService()
        _reset_debounce_cache()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)
        self.env_patch.stop()
        store.close_connection()
        store.DB_DIR = self._original_db_dir
        store.DB_PATH = self._original_db_path
        store._connection = None
        self.temp_dir.cleanup()
        _reset_debounce_cache()

    def _admin_headers(self) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login",
            json={"username": "track.admin", "password": "track-password"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    # --- tests ------------------------------------------------------------

    def test_authenticated_track_writes_audit_log(self):
        headers = self._admin_headers()
        response = self.client.post(
            "/api/audit/track",
            headers=headers,
            json={
                "module": "daily_intake",
                "action": "voice_record_start",
                "description": "/daily-intake",
                "metadata": {"category": "vegetable"},
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertFalse(body["throttled"])

        logs = self.audit_service.list_logs(
            limit=50, module="daily_intake", action="voice_record_start"
        )
        self.assertEqual(len(logs), 1)
        entry = logs[0]
        self.assertEqual(entry.module, "daily_intake")
        self.assertEqual(entry.action, "voice_record_start")
        self.assertIn("/daily-intake", entry.description)
        self.assertIn("category", entry.description)
        self.assertEqual(entry.result, "success")

    def test_unauthenticated_track_is_rejected(self):
        response = self.client.post(
            "/api/audit/track",
            json={"module": "navigation", "action": "page_view"},
        )
        self.assertEqual(response.status_code, 401)

    def test_duplicate_events_within_debounce_window_are_throttled(self):
        headers = self._admin_headers()
        payload = {"module": "navigation", "action": "page_view", "description": "/x"}

        first = self.client.post("/api/audit/track", headers=headers, json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json()["throttled"])

        second = self.client.post("/api/audit/track", headers=headers, json=payload)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["throttled"])

        logs = self.audit_service.list_logs(
            limit=10, module="navigation", action="page_view"
        )
        self.assertEqual(len(logs), 1, logs)

    def test_invalid_payload_is_rejected(self):
        headers = self._admin_headers()
        response = self.client.post(
            "/api/audit/track",
            headers=headers,
            json={"module": "", "action": ""},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
