import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.db.store as store
from app.db.auth_repository import AuthRepository
from backend.main import app


class AuthDeviceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "auth-devices-test.db")
        store._connection = None

        self.env_patch = patch.dict(
            os.environ,
            {
                "SEED_SUPER_ADMIN_USERNAME": "lina1124",
                "SEED_SUPER_ADMIN_PASSWORD": "initial-secret",
                "SEED_SUPER_ADMIN_FORCE_CHANGE_PASSWORD": "true",
                "AUTH_ACCESS_TOKEN_MINUTES": "60",
                "AUTH_REFRESH_TOKEN_DAYS": "14",
                "AUTH_PENDING_LOGIN_MINUTES": "10",
                "AUTH_MAX_DEVICES_PER_ACCOUNT": "10",
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

    def test_devices_require_authentication(self):
        response = self.client.get("/api/auth/devices")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "AUTH_REQUIRED")

    def test_login_registers_current_device_for_listing(self):
        token = self.register_and_login(
            username="device.member",
            password="member-password",
            device_name="office laptop",
            user_agent="DeviceTest/office",
        )

        response = self.client.get("/api/auth/devices", headers=self.auth_headers(token))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        device = body["devices"][0]
        self.assertEqual(device["device_name"], "office laptop")
        self.assertEqual(device["user_agent"], "DeviceTest/office")
        self.assertTrue(device["is_current"])
        self.assertFalse(device["is_revoked"])
        self.assertEqual(device["active_session_count"], 1)

    def test_device_can_be_renamed(self):
        token = self.register_and_login(
            username="rename.member",
            password="member-password",
            device_name="old name",
            user_agent="DeviceTest/rename",
        )
        list_response = self.client.get("/api/auth/devices", headers=self.auth_headers(token))
        device_id = list_response.json()["devices"][0]["id"]

        rename_response = self.client.put(
            f"/api/auth/devices/{device_id}",
            json={"device_name": "front desk tablet"},
            headers=self.auth_headers(token),
        )

        self.assertEqual(rename_response.status_code, 200)
        self.assertTrue(rename_response.json()["success"])
        self.assertEqual(rename_response.json()["device"]["device_name"], "front desk tablet")

        refreshed_response = self.client.get("/api/auth/devices", headers=self.auth_headers(token))
        self.assertEqual(refreshed_response.json()["devices"][0]["device_name"], "front desk tablet")

    def test_device_revoke_invalidates_sessions_on_that_device_only(self):
        username = "multi.device"
        password = "member-password"
        self.register_user(username, password)

        first_token = self.login(username, password, "front desk pc", "DeviceTest/pc")
        second_token = self.login(username, password, "warehouse tablet", "DeviceTest/tablet")

        list_response = self.client.get("/api/auth/devices", headers=self.auth_headers(second_token))
        self.assertEqual(list_response.status_code, 200)
        devices = list_response.json()["devices"]
        self.assertEqual(len(devices), 2)
        first_device = next(device for device in devices if device["user_agent"] == "DeviceTest/pc")
        current_device = next(device for device in devices if device["is_current"])
        self.assertEqual(current_device["user_agent"], "DeviceTest/tablet")

        revoke_response = self.client.delete(
            f"/api/auth/devices/{first_device['id']}",
            headers=self.auth_headers(second_token),
        )

        self.assertEqual(revoke_response.status_code, 200)
        self.assertTrue(revoke_response.json()["device"]["is_revoked"])
        self.assertEqual(revoke_response.json()["device"]["active_session_count"], 0)

        revoked_me_response = self.client.get("/api/auth/me", headers=self.auth_headers(first_token))
        self.assertEqual(revoked_me_response.status_code, 401)
        self.assertEqual(revoked_me_response.json()["detail"]["code"], "INVALID_TOKEN")

        current_me_response = self.client.get("/api/auth/me", headers=self.auth_headers(second_token))
        self.assertEqual(current_me_response.status_code, 200)

    def test_current_device_revoke_clears_cookie_and_invalidates_current_session(self):
        token = self.register_and_login(
            username="current.device",
            password="member-password",
            device_name="current browser",
            user_agent="DeviceTest/current",
        )
        list_response = self.client.get("/api/auth/devices", headers=self.auth_headers(token))
        device_id = list_response.json()["devices"][0]["id"]

        revoke_response = self.client.delete(f"/api/auth/devices/{device_id}", headers=self.auth_headers(token))

        self.assertEqual(revoke_response.status_code, 200)
        self.assertTrue(revoke_response.json()["device"]["is_current"])
        self.assert_refresh_cookie_is_cleared(revoke_response)

        me_response = self.client.get("/api/auth/me", headers=self.auth_headers(token))
        self.assertEqual(me_response.status_code, 401)
        self.assertEqual(me_response.json()["detail"]["code"], "INVALID_TOKEN")

    def test_device_permission_is_required(self):
        register_response = self.register_user("denied.device", "member-password")
        user_id = register_response.json()["user"]["id"]
        AuthRepository.upsert_user_permission_override(
            user_id=user_id,
            permission_code="device:view",
            effect="deny",
            reason="device list denied",
        )
        token = self.login("denied.device", "member-password", "denied", "DeviceTest/denied")

        response = self.client.get("/api/auth/devices", headers=self.auth_headers(token))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "PERMISSION_DENIED")

    def test_eleventh_new_device_returns_pending_login_without_tokens(self):
        username = "limit.pending"
        password = "member-password"
        self.register_user(username, password)
        for index in range(10):
            self.login(username, password, f"device {index}", f"DeviceLimit/{index}")

        response = self.raw_login(username, password, "new device", "DeviceLimit/new")

        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertTrue(body["requires_device_replacement"])
        self.assertTrue(body["pending_token"])
        self.assertEqual(body["max_devices"], 10)
        self.assertEqual(len(body["devices"]), 10)
        self.assertNotIn("access_token", body)
        self.assertNotIn("refresh_token", body)
        self.assertNotIn("set-cookie", {key.lower(): value for key, value in response.headers.items()})

        user = AuthRepository.get_user_by_username(username)
        active_devices = store.query_one(
            "SELECT COUNT(*) AS count FROM auth_devices WHERE user_id = ? AND is_revoked = 0",
            (user["id"],),
        )
        active_sessions = store.query_one(
            "SELECT COUNT(*) AS count FROM auth_sessions WHERE user_id = ? AND revoked_at IS NULL",
            (user["id"],),
        )
        self.assertEqual(active_devices["count"], 10)
        self.assertEqual(active_sessions["count"], 10)

    def test_pending_login_can_replace_old_device_and_login_new_device(self):
        username = "limit.replace"
        password = "member-password"
        self.register_user(username, password)
        first_token = self.login(username, password, "device 0", "DeviceReplace/0")
        last_token = first_token
        for index in range(1, 10):
            last_token = self.login(username, password, f"device {index}", f"DeviceReplace/{index}")

        devices_response = self.client.get("/api/auth/devices", headers=self.auth_headers(last_token))
        replaced_device = next(device for device in devices_response.json()["devices"] if device["user_agent"] == "DeviceReplace/0")
        pending_response = self.raw_login(username, password, "new device", "DeviceReplace/new")
        self.assertEqual(pending_response.status_code, 202)

        replacement_response = self.client.post(
            "/api/auth/device-replacement",
            json={
                "pending_token": pending_response.json()["pending_token"],
                "replace_device_id": replaced_device["id"],
            },
        )

        self.assertEqual(replacement_response.status_code, 200)
        self.assert_refresh_cookie_is_set(replacement_response)
        replacement_body = replacement_response.json()
        self.assertTrue(replacement_body["access_token"])
        self.assertEqual(replacement_body["user"]["username"], username)

        revoked_me_response = self.client.get("/api/auth/me", headers=self.auth_headers(first_token))
        self.assertEqual(revoked_me_response.status_code, 401)
        self.assertEqual(revoked_me_response.json()["detail"]["code"], "INVALID_TOKEN")

        new_token = replacement_body["access_token"]
        new_me_response = self.client.get("/api/auth/me", headers=self.auth_headers(new_token))
        self.assertEqual(new_me_response.status_code, 200)

        user = AuthRepository.get_user_by_username(username)
        active_devices = store.query_one(
            "SELECT COUNT(*) AS count FROM auth_devices WHERE user_id = ? AND is_revoked = 0",
            (user["id"],),
        )
        self.assertEqual(active_devices["count"], 10)

    def test_existing_active_device_can_login_when_limit_is_reached(self):
        username = "limit.existing"
        password = "member-password"
        self.register_user(username, password)
        for index in range(10):
            self.login(username, password, f"device {index}", f"DeviceExisting/{index}")

        response = self.raw_login(username, password, "device 0 again", "DeviceExisting/0")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["access_token"])
        user = AuthRepository.get_user_by_username(username)
        active_devices = store.query_one(
            "SELECT COUNT(*) AS count FROM auth_devices WHERE user_id = ? AND is_revoked = 0",
            (user["id"],),
        )
        self.assertEqual(active_devices["count"], 10)

    def test_expired_pending_login_cannot_replace_device(self):
        username = "limit.expired"
        password = "member-password"
        self.register_user(username, password)
        last_token = ""
        for index in range(10):
            last_token = self.login(username, password, f"device {index}", f"DeviceExpired/{index}")

        devices_response = self.client.get("/api/auth/devices", headers=self.auth_headers(last_token))
        replace_device_id = devices_response.json()["devices"][0]["id"]
        pending_response = self.raw_login(username, password, "new device", "DeviceExpired/new")
        self.assertEqual(pending_response.status_code, 202)
        store.get_connection().execute(
            "UPDATE auth_pending_logins SET expires_at = ?",
            ("2000-01-01T00:00:00+00:00",),
        )
        store.get_connection().commit()

        replacement_response = self.client.post(
            "/api/auth/device-replacement",
            json={
                "pending_token": pending_response.json()["pending_token"],
                "replace_device_id": replace_device_id,
            },
        )

        self.assertEqual(replacement_response.status_code, 401)
        self.assertEqual(replacement_response.json()["detail"]["code"], "PENDING_LOGIN_EXPIRED")

    def register_user(self, username: str, password: str):
        response = self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password, "display_name": username},
        )
        self.assertEqual(response.status_code, 200)
        return response

    def register_and_login(self, *, username: str, password: str, device_name: str, user_agent: str) -> str:
        self.register_user(username, password)
        return self.login(username, password, device_name, user_agent)

    def login(self, username: str, password: str, device_name: str, user_agent: str) -> str:
        response = self.raw_login(username, password, device_name, user_agent)
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def raw_login(self, username: str, password: str, device_name: str, user_agent: str):
        return self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password, "device_name": device_name},
            headers={"user-agent": user_agent},
        )

    @staticmethod
    def auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def assert_refresh_cookie_is_cleared(self, response):
        set_cookie = response.headers.get("set-cookie", "").lower()
        self.assertIn("auth_refresh_token=", set_cookie)
        self.assertIn("max-age=0", set_cookie)

    def assert_refresh_cookie_is_set(self, response):
        set_cookie = response.headers.get("set-cookie", "").lower()
        self.assertIn("auth_refresh_token=", set_cookie)
        self.assertIn("httponly", set_cookie)


if __name__ == "__main__":
    unittest.main()
