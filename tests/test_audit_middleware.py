"""End-to-end checks for the automatic audit middleware."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db import store
from backend.main import app
from backend.services.audit_log_service import AuditLogService


class AuditMiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self._original_db_dir = store.DB_DIR
        self._original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "audit-middleware.db")
        store._connection = None

        self.env_patch = patch.dict(
            os.environ,
            {
                "SEED_SUPER_ADMIN_USERNAME": "audit.admin",
                "SEED_SUPER_ADMIN_PASSWORD": "audit-password",
                "SEED_SUPER_ADMIN_FORCE_CHANGE_PASSWORD": "false",
            },
            clear=False,
        )
        self.env_patch.start()

        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()
        self.audit_service = AuditLogService()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)
        self.env_patch.stop()
        store.close_connection()
        store.DB_DIR = self._original_db_dir
        store.DB_PATH = self._original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def _admin_headers(self) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login",
            json={"username": "audit.admin", "password": "audit-password"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _logs(self, **filters):
        return self.audit_service.list_logs(limit=200, **filters)

    # --- tests ------------------------------------------------------------

    def test_mutating_request_generates_audit_entry(self):
        headers = self._admin_headers()
        before = len(self._logs(module="pesticide"))

        response = self.client.post(
            "/api/pesticide/dedup-json",
            headers=headers,
            json={"json_text": "[]"},
        )
        self.assertEqual(response.status_code, 200, response.text)

        after = self._logs(module="pesticide")
        self.assertGreater(len(after), before)
        latest = after[0]
        self.assertTrue(latest.action.startswith("POST "))
        self.assertEqual(latest.result, "success")
        self.assertIn("status=200", latest.description)

    def test_failure_response_is_recorded_as_failure(self):
        headers = self._admin_headers()
        # Intentional bad payload: dedup-json requires json_text; empty body 422.
        response = self.client.post(
            "/api/pesticide/dedup-json", headers=headers, json={}
        )
        self.assertEqual(response.status_code, 422)

        logs = self._logs(module="pesticide", result="failure")
        self.assertTrue(any("status=422" in row.description for row in logs), logs)

    def test_get_request_is_not_audited_by_middleware(self):
        headers = self._admin_headers()
        response = self.client.get("/api/config/", headers=headers)
        self.assertEqual(response.status_code, 200)

        logs = self._logs(module="config")
        # GET should not produce a config audit entry.
        self.assertFalse(
            any(row.action.startswith("GET ") for row in logs),
            logs,
        )

    def test_audit_track_endpoint_is_skipped_to_avoid_recursion(self):
        from backend.api.routes.audit import _reset_debounce_cache

        _reset_debounce_cache()
        headers = self._admin_headers()

        response = self.client.post(
            "/api/audit/track",
            headers=headers,
            json={"module": "navigation", "action": "page_view", "description": "/x"},
        )
        self.assertEqual(response.status_code, 200, response.text)

        # The track endpoint writes its own entry; the middleware must NOT add
        # a second POST /api/audit/track entry for the same request.
        logs = self._logs(module="navigation", action="page_view")
        self.assertEqual(len(logs), 1, logs)
        self.assertFalse(logs[0].action.startswith("POST "))

    def test_auth_login_is_not_double_audited_by_middleware(self):
        # After setUp seeds the admin, calling login itself triggers the
        # auth.py manual audit entry but the middleware should skip it.
        before = len(self._logs(module="auth"))
        self._admin_headers()  # performs a login
        after_logs = self._logs(module="auth")

        post_login_count = sum(
            1 for row in after_logs if row.action.startswith("POST /api/auth/login")
        )
        self.assertEqual(post_login_count, 0, after_logs)
        # But the manual "login" audit entry is still present.
        self.assertGreater(len(after_logs), before)


if __name__ == "__main__":
    unittest.main()
