import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.db.store as store
from app.db.auth_repository import AuthRepository
from backend.main import app


class AuthPermissionRequestApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "auth-permission-requests-test.db")
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

    def test_member_can_create_and_list_own_permission_request(self):
        token = self.register_and_login("request.member", "member-password")

        permissions_response = self.client.get("/api/auth/permissions", headers=self.auth_headers(token))
        self.assertEqual(permissions_response.status_code, 200)
        inventory_permission = next(item for item in permissions_response.json()["permissions"] if item["code"] == "inventory:view")
        self.assertFalse(inventory_permission["has_permission"])

        create_response = self.client.post(
            "/api/auth/permission-requests",
            json={"permission_code": "inventory:view", "reason": "Need to check stock"},
            headers=self.auth_headers(token),
        )

        self.assertEqual(create_response.status_code, 200)
        body = create_response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["request"]["permission_code"], "inventory:view")
        self.assertEqual(body["request"]["status"], "pending")
        self.assertEqual(body["request"]["username"], "request.member")

        mine_response = self.client.get("/api/auth/permission-requests/mine", headers=self.auth_headers(token))
        self.assertEqual(mine_response.status_code, 200)
        self.assertEqual(mine_response.json()["total"], 1)
        self.assertEqual(mine_response.json()["requests"][0]["reason"], "Need to check stock")

    def test_duplicate_pending_request_is_rejected(self):
        token = self.register_and_login("duplicate.request", "member-password")
        payload = {"permission_code": "weekly_quote:view", "reason": "Need quote access"}

        first_response = self.client.post("/api/auth/permission-requests", json=payload, headers=self.auth_headers(token))
        second_response = self.client.post("/api/auth/permission-requests", json=payload, headers=self.auth_headers(token))

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.json()["detail"]["code"], "PERMISSION_REQUEST_PENDING")

    def test_requesting_existing_permission_is_rejected(self):
        token = self.register_and_login("granted.request", "member-password")

        response = self.client.post(
            "/api/auth/permission-requests",
            json={"permission_code": "dashboard:view", "reason": "Already available"},
            headers=self.auth_headers(token),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "PERMISSION_ALREADY_GRANTED")

    def test_super_admin_can_approve_request_and_grant_permission(self):
        member_token = self.register_and_login("approve.member", "member-password")
        create_response = self.client.post(
            "/api/auth/permission-requests",
            json={"permission_code": "inventory:view", "reason": "Inventory work"},
            headers=self.auth_headers(member_token),
        )
        request_id = create_response.json()["request"]["id"]
        admin_token = self.login("lina1124", "initial-secret")

        pending_response = self.client.get(
            "/api/auth/permission-requests?status=pending",
            headers=self.auth_headers(admin_token),
        )
        self.assertEqual(pending_response.status_code, 200)
        self.assertEqual(pending_response.json()["total"], 1)

        review_response = self.client.post(
            f"/api/auth/permission-requests/{request_id}/review",
            json={"status": "approved", "review_comment": "Approved for stock work"},
            headers=self.auth_headers(admin_token),
        )

        self.assertEqual(review_response.status_code, 200)
        reviewed = review_response.json()["request"]
        self.assertEqual(reviewed["status"], "approved")
        self.assertEqual(reviewed["reviewer_username"], "lina1124")

        me_response = self.client.get("/api/auth/me", headers=self.auth_headers(member_token))
        self.assertEqual(me_response.status_code, 200)
        self.assertIn("inventory:view", me_response.json()["user"]["permissions"])

    def test_rejected_request_does_not_grant_permission(self):
        member_token = self.register_and_login("reject.member", "member-password")
        create_response = self.client.post(
            "/api/auth/permission-requests",
            json={"permission_code": "transfer:view", "reason": "Need transfer access"},
            headers=self.auth_headers(member_token),
        )
        request_id = create_response.json()["request"]["id"]
        admin_token = self.login("lina1124", "initial-secret")

        review_response = self.client.post(
            f"/api/auth/permission-requests/{request_id}/review",
            json={"status": "rejected", "review_comment": "Not needed now"},
            headers=self.auth_headers(admin_token),
        )

        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(review_response.json()["request"]["status"], "rejected")

        me_response = self.client.get("/api/auth/me", headers=self.auth_headers(member_token))
        self.assertEqual(me_response.status_code, 200)
        self.assertNotIn("transfer:view", me_response.json()["user"]["permissions"])

    def test_reviewed_request_cannot_be_reviewed_again(self):
        member_token = self.register_and_login("reviewed.member", "member-password")
        create_response = self.client.post(
            "/api/auth/permission-requests",
            json={"permission_code": "pesticide:view", "reason": "Need pesticide access"},
            headers=self.auth_headers(member_token),
        )
        request_id = create_response.json()["request"]["id"]
        admin_token = self.login("lina1124", "initial-secret")

        first_review = self.client.post(
            f"/api/auth/permission-requests/{request_id}/review",
            json={"status": "approved", "review_comment": "ok"},
            headers=self.auth_headers(admin_token),
        )
        second_review = self.client.post(
            f"/api/auth/permission-requests/{request_id}/review",
            json={"status": "rejected", "review_comment": "late reject"},
            headers=self.auth_headers(admin_token),
        )

        self.assertEqual(first_review.status_code, 200)
        self.assertEqual(second_review.status_code, 409)
        self.assertEqual(second_review.json()["detail"]["code"], "PERMISSION_REQUEST_NOT_PENDING")

    def test_member_cannot_list_or_review_all_requests(self):
        member_token = self.register_and_login("plain.member", "member-password")

        list_response = self.client.get("/api/auth/permission-requests", headers=self.auth_headers(member_token))
        review_response = self.client.post(
            "/api/auth/permission-requests/1/review",
            json={"status": "approved", "review_comment": "nope"},
            headers=self.auth_headers(member_token),
        )

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(list_response.json()["detail"]["code"], "PERMISSION_DENIED")
        self.assertEqual(review_response.status_code, 403)
        self.assertEqual(review_response.json()["detail"]["code"], "PERMISSION_DENIED")

    def test_admin_role_can_approve_requests(self):
        member_token = self.register_and_login("admin.approve.member", "member-password")
        create_response = self.client.post(
            "/api/auth/permission-requests",
            json={"permission_code": "daily_check:view", "reason": "Daily intake work"},
            headers=self.auth_headers(member_token),
        )
        request_id = create_response.json()["request"]["id"]
        admin_token = self.register_admin_and_login("request.admin", "member-password")

        response = self.client.post(
            f"/api/auth/permission-requests/{request_id}/review",
            json={"status": "approved", "review_comment": "admin approved"},
            headers=self.auth_headers(admin_token),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["request"]["status"], "approved")

    def register_and_login(self, username: str, password: str) -> str:
        register_response = self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password, "display_name": username},
        )
        self.assertEqual(register_response.status_code, 200)
        return self.login(username, password)

    def register_admin_and_login(self, username: str, password: str) -> str:
        self.register_and_login(username, password)
        user = AuthRepository.get_user_by_username(username)
        role = store.query_one("SELECT id FROM auth_roles WHERE code = 'admin'")
        store.get_connection().execute(
            "INSERT OR IGNORE INTO auth_user_roles (user_id, role_id) VALUES (?, ?)",
            (user["id"], role["id"]),
        )
        store.get_connection().commit()
        return self.login(username, password)

    def login(self, username: str, password: str) -> str:
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password, "device_name": "test browser"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    @staticmethod
    def auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    unittest.main()
