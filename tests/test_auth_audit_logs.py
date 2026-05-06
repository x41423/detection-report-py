import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.db.store as store
from backend.main import app


class AuthAuditLogApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "auth-audit-log-test.db")
        store._connection = None

        self.env_patch = patch.dict(
            os.environ,
            {
                "SEED_SUPER_ADMIN_USERNAME": "lina1124",
                "SEED_SUPER_ADMIN_PASSWORD": "initial-secret",
                "SEED_SUPER_ADMIN_FORCE_CHANGE_PASSWORD": "true",
                "AUTH_ACCESS_TOKEN_MINUTES": "60",
                "AUTH_REFRESH_TOKEN_DAYS": "14",
            },
            clear=False,
        )
        self.env_patch.start()
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)
        self.env_patch.stop()
        store.close_connection()
        store.DB_DIR = self.original_db_dir
        store.DB_PATH = self.original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def test_super_admin_can_query_audit_logs_and_filter_by_module(self):
        token = self.login("lina1124", "initial-secret")

        create_response = self.client.post(
            "/api/auth/users",
            json={
                "username": "audited.user",
                "password": "audited-password",
                "display_name": "Audited User",
                "role_codes": ["member"],
            },
            headers=self.auth_headers(token),
        )
        self.assertEqual(create_response.status_code, 200)

        list_response = self.client.get("/api/auth/audit-logs?limit=20", headers=self.auth_headers(token))

        self.assertEqual(list_response.status_code, 200)
        body = list_response.json()
        actions = {log["action"] for log in body["logs"]}
        self.assertGreaterEqual(body["total"], 2)
        self.assertIn("login", actions)
        self.assertIn("user_create", actions)

        user_filter_response = self.client.get(
            "/api/auth/audit-logs?module=user&limit=20",
            headers=self.auth_headers(token),
        )
        self.assertEqual(user_filter_response.status_code, 200)
        user_logs = user_filter_response.json()["logs"]
        self.assertTrue(user_logs)
        self.assertTrue(all(log["module"] == "user" for log in user_logs))
        create_log = next(log for log in user_logs if log["action"] == "user_create")
        self.assertEqual(create_log["actor_username"], "lina1124")
        self.assertEqual(create_log["target_username"], "audited.user")
        self.assertEqual(create_log["result"], "success")

    def test_failed_login_is_audited_without_leaking_secret(self):
        failed_login = self.client.post(
            "/api/auth/login",
            json={"username": "lina1124", "password": "wrong-password"},
        )
        self.assertEqual(failed_login.status_code, 401)
        token = self.login("lina1124", "initial-secret")

        response = self.client.get(
            "/api/auth/audit-logs?action=login&result=failure&limit=10",
            headers=self.auth_headers(token),
        )

        self.assertEqual(response.status_code, 200)
        logs = response.json()["logs"]
        self.assertEqual(len(logs), 1)
        log = logs[0]
        self.assertEqual(log["target_username"], "lina1124")
        self.assertIn("INVALID_CREDENTIALS", log["description"])
        self.assertNotIn("wrong-password", log["description"])

    def test_member_cannot_query_audit_logs(self):
        token = self.register_and_login("audit.member", "member-password")

        response = self.client.get("/api/auth/audit-logs", headers=self.auth_headers(token))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "PERMISSION_DENIED")

    def register_and_login(self, username: str, password: str) -> str:
        register_response = self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password, "display_name": username},
        )
        self.assertEqual(register_response.status_code, 200)
        return self.login(username, password)

    def login(self, username: str, password: str) -> str:
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password, "device_name": "test browser"},
            headers={"user-agent": "AuditTest/1.0"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    @staticmethod
    def auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    unittest.main()
