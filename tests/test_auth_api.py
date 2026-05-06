import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.db.store as store
from backend.main import app


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "auth-api-test.db")
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

    def test_me_requires_token(self):
        response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "AUTH_REQUIRED")

    def test_seeded_super_admin_can_login_and_read_me(self):
        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": "lina1124",
                "password": "initial-secret",
                "device_name": "test browser",
            },
        )

        self.assertEqual(login_response.status_code, 200)
        login_body = login_response.json()
        self.assertEqual(login_body["token_type"], "bearer")
        self.assertTrue(login_body["access_token"])
        self.assertNotIn("refresh_token", login_body)
        self.assert_refresh_cookie_is_set(login_response)
        self.assertIn("super_admin", login_body["user"]["roles"])
        self.assertIn("dashboard:view", login_body["user"]["permissions"])
        self.assertTrue(login_body["user"]["is_super_admin"])
        self.assertTrue(login_body["user"]["must_change_password"])

        me_response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {login_body['access_token']}"},
        )

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["user"]["username"], "lina1124")

    def test_register_member_then_login_and_logout(self):
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "username": "new.member",
                "password": "member-password",
                "display_name": "New Member",
            },
        )

        self.assertEqual(register_response.status_code, 200)
        register_body = register_response.json()
        self.assertTrue(register_body["success"])
        self.assertEqual(register_body["user"]["username"], "new.member")
        self.assertEqual(register_body["user"]["display_name"], "New Member")
        self.assertEqual(register_body["user"]["roles"], ["member"])
        self.assertIn("permission_request:create", register_body["user"]["permissions"])
        self.assertFalse(register_body["user"]["is_super_admin"])

        login_response = self.client.post(
            "/api/auth/login",
            json={
                "username": "NEW.Member",
                "password": "member-password",
                "device_name": "member browser",
            },
        )
        self.assertEqual(login_response.status_code, 200)
        token = login_response.json()["access_token"]

        me_response = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["user"]["username"], "new.member")

        logout_response = self.client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(logout_response.status_code, 200)
        self.assertTrue(logout_response.json()["success"])
        self.assert_refresh_cookie_is_cleared(logout_response)

        revoked_response = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(revoked_response.status_code, 401)
        self.assertEqual(revoked_response.json()["detail"]["code"], "INVALID_TOKEN")

        refresh_response = self.client.post("/api/auth/refresh")
        self.assertEqual(refresh_response.status_code, 401)
        self.assertEqual(refresh_response.json()["detail"]["code"], "REFRESH_REQUIRED")

    def test_register_rejects_duplicate_username(self):
        payload = {"username": "duplicate", "password": "duplicate-password"}

        first_response = self.client.post("/api/auth/register", json=payload)
        second_response = self.client.post("/api/auth/register", json=payload)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json()["detail"]["code"], "USERNAME_EXISTS")

    def test_login_rejects_bad_password_without_leaking_user_state(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "lina1124", "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)
        body = response.json()
        self.assertEqual(body["detail"]["code"], "INVALID_CREDENTIALS")
        self.assertEqual(body["detail"]["message"], "用户名或密码错误")

    def test_refresh_rotates_refresh_cookie_and_issues_new_access_token(self):
        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "lina1124", "password": "initial-secret"},
        )
        self.assertEqual(login_response.status_code, 200)
        original_access_token = login_response.json()["access_token"]
        original_refresh_token = self.client.cookies.get("auth_refresh_token")
        self.assertTrue(original_refresh_token)

        refresh_response = self.client.post("/api/auth/refresh")

        self.assertEqual(refresh_response.status_code, 200)
        self.assert_refresh_cookie_is_set(refresh_response)
        refresh_body = refresh_response.json()
        self.assertNotEqual(refresh_body["access_token"], original_access_token)
        self.assertEqual(refresh_body["user"]["username"], "lina1124")
        self.assertTrue(self.client.cookies.get("auth_refresh_token"))
        self.assertNotEqual(self.client.cookies.get("auth_refresh_token"), original_refresh_token)

        self.client.cookies.clear()
        self.client.cookies.set("auth_refresh_token", original_refresh_token)
        replay_response = self.client.post("/api/auth/refresh")
        self.assertEqual(replay_response.status_code, 401)
        self.assertEqual(replay_response.json()["detail"]["code"], "INVALID_REFRESH_TOKEN")

    def test_expired_access_token_can_be_refreshed_with_valid_refresh_cookie(self):
        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "lina1124", "password": "initial-secret"},
        )
        self.assertEqual(login_response.status_code, 200)
        access_token = login_response.json()["access_token"]
        store.get_connection().execute(
            "UPDATE auth_sessions SET access_expires_at = ?",
            ("2000-01-01T00:00:00+00:00",),
        )
        store.get_connection().commit()

        me_response = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        self.assertEqual(me_response.status_code, 401)
        self.assertEqual(me_response.json()["detail"]["code"], "TOKEN_EXPIRED")

        refresh_response = self.client.post("/api/auth/refresh")
        self.assertEqual(refresh_response.status_code, 200)
        refreshed_token = refresh_response.json()["access_token"]
        self.assertNotEqual(refreshed_token, access_token)

        refreshed_me_response = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {refreshed_token}"})
        self.assertEqual(refreshed_me_response.status_code, 200)
        self.assertEqual(refreshed_me_response.json()["user"]["username"], "lina1124")

    def test_expired_refresh_token_revokes_session_and_clears_cookie(self):
        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "lina1124", "password": "initial-secret"},
        )
        self.assertEqual(login_response.status_code, 200)
        store.get_connection().execute(
            "UPDATE auth_sessions SET refresh_expires_at = ?",
            ("2000-01-01T00:00:00+00:00",),
        )
        store.get_connection().commit()

        refresh_response = self.client.post("/api/auth/refresh")

        self.assertEqual(refresh_response.status_code, 401)
        self.assertEqual(refresh_response.json()["detail"]["code"], "REFRESH_TOKEN_EXPIRED")
        self.assert_refresh_cookie_is_cleared(refresh_response)
        session = store.query_one("SELECT revoked_at, revoke_reason FROM auth_sessions")
        self.assertIsNotNone(session["revoked_at"])
        self.assertEqual(session["revoke_reason"], "refresh_expired")

    def assert_refresh_cookie_is_set(self, response):
        set_cookie = response.headers.get("set-cookie", "").lower()
        self.assertIn("auth_refresh_token=", set_cookie)
        self.assertIn("httponly", set_cookie)
        self.assertIn("samesite=lax", set_cookie)
        self.assertIn("path=/api/auth", set_cookie)

    def assert_refresh_cookie_is_cleared(self, response):
        set_cookie = response.headers.get("set-cookie", "").lower()
        self.assertIn("auth_refresh_token=", set_cookie)
        self.assertIn("max-age=0", set_cookie)


if __name__ == "__main__":
    unittest.main()
