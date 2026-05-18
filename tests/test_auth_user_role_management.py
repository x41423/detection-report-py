import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.db.store as store
from app.db.auth_repository import AuthRepository
from backend.main import app


class AuthUserRoleManagementApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "auth-user-role-management-test.db")
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

    def test_super_admin_can_create_update_and_disable_user(self):
        admin_token = self.login("lina1124", "initial-secret")

        create_response = self.client.post(
            "/api/auth/users",
            json={
                "username": "managed.user",
                "password": "managed-password",
                "display_name": "Managed User",
                "role_codes": ["member"],
            },
            headers=self.auth_headers(admin_token),
        )

        self.assertEqual(create_response.status_code, 200)
        user = create_response.json()["user"]
        self.assertEqual(user["username"], "managed.user")
        self.assertEqual(user["roles"], ["member"])

        update_response = self.client.patch(
            f"/api/auth/users/{user['id']}",
            json={"display_name": "Managed Admin", "role_codes": ["admin"], "is_active": False},
            headers=self.auth_headers(admin_token),
        )

        self.assertEqual(update_response.status_code, 200)
        updated_user = update_response.json()["user"]
        self.assertEqual(updated_user["display_name"], "Managed Admin")
        self.assertEqual(updated_user["roles"], ["admin"])
        self.assertFalse(updated_user["is_active"])

        login_response = self.client.post(
            "/api/auth/login",
            json={"username": "managed.user", "password": "managed-password"},
        )
        self.assertEqual(login_response.status_code, 403)
        self.assertEqual(login_response.json()["detail"]["code"], "ACCOUNT_DISABLED")

    def test_member_cannot_list_users_or_roles(self):
        token = self.register_and_login("plain.member", "member-password")

        users_response = self.client.get("/api/auth/users", headers=self.auth_headers(token))
        roles_response = self.client.get("/api/auth/roles", headers=self.auth_headers(token))

        self.assertEqual(users_response.status_code, 403)
        self.assertEqual(users_response.json()["detail"]["code"], "PERMISSION_DENIED")
        self.assertEqual(roles_response.status_code, 403)
        self.assertEqual(roles_response.json()["detail"]["code"], "PERMISSION_DENIED")

    def test_admin_cannot_modify_super_admin(self):
        admin_token = self.register_admin_and_login("limited.admin", "member-password")
        super_admin = AuthRepository.get_user_by_username("lina1124")

        response = self.client.patch(
            f"/api/auth/users/{super_admin['id']}",
            json={"is_active": False},
            headers=self.auth_headers(admin_token),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "SUPER_ADMIN_PROTECTED")

    def test_super_admin_can_delete_regular_user_and_cascade_auth_records(self):
        admin_token = self.login("lina1124", "initial-secret")
        create_response = self.client.post(
            "/api/auth/users",
            json={
                "username": "delete.target",
                "password": "delete-password",
                "display_name": "Delete Target",
                "role_codes": ["member"],
            },
            headers=self.auth_headers(admin_token),
        )
        self.assertEqual(create_response.status_code, 200)
        user = create_response.json()["user"]
        user_id = user["id"]

        user_token = self.login("delete.target", "delete-password")
        request_response = self.client.post(
            "/api/auth/permission-requests",
            json={"permission_code": "inventory:view", "reason": "temporary access"},
            headers=self.auth_headers(user_token),
        )
        self.assertEqual(request_response.status_code, 200)
        refresh_response = self.client.post("/api/auth/refresh")
        self.assertEqual(refresh_response.status_code, 200)

        self.assertGreater(self.count_rows("auth_user_roles", user_id), 0)
        self.assertGreater(self.count_rows("auth_devices", user_id), 0)
        self.assertGreater(self.count_rows("auth_sessions", user_id), 0)
        self.assertGreater(self.count_rows("auth_permission_requests", user_id), 0)
        self.assertGreater(
            store.query_one(
                """
                SELECT COUNT(*) AS count
                FROM auth_refresh_token_grace g
                JOIN auth_sessions s ON s.id = g.session_id
                WHERE s.user_id = ?
                """,
                (user_id,),
            )["count"],
            0,
        )

        delete_response = self.client.delete(f"/api/auth/users/{user_id}", headers=self.auth_headers(admin_token))

        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["success"])
        self.assertIsNone(AuthRepository.get_user_by_id(user_id))
        users_response = self.client.get("/api/auth/users", headers=self.auth_headers(admin_token))
        self.assertNotIn("delete.target", [item["username"] for item in users_response.json()["users"]])
        deleted_login_response = self.client.post(
            "/api/auth/login",
            json={"username": "delete.target", "password": "delete-password"},
        )
        self.assertEqual(deleted_login_response.status_code, 401)
        self.assertEqual(deleted_login_response.json()["detail"]["code"], "INVALID_CREDENTIALS")
        self.assertEqual(self.count_rows("auth_user_roles", user_id), 0)
        self.assertEqual(self.count_rows("auth_devices", user_id), 0)
        self.assertEqual(self.count_rows("auth_sessions", user_id), 0)
        self.assertEqual(self.count_rows("auth_permission_requests", user_id), 0)
        audit_log = store.query_one("SELECT * FROM auth_audit_logs WHERE action = 'user_delete'")
        self.assertIsNotNone(audit_log)
        self.assertIsNone(audit_log["target_user_id"])
        self.assertIn("delete.target", audit_log["description"])
        self.assertIn(str(user_id), audit_log["description"])

    def test_delete_user_rejects_missing_super_admin_and_non_super_admin_actor(self):
        admin_token = self.login("lina1124", "initial-secret")
        missing_response = self.client.delete("/api/auth/users/999999", headers=self.auth_headers(admin_token))
        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(missing_response.json()["detail"]["code"], "USER_NOT_FOUND")

        super_admin = AuthRepository.get_user_by_username("lina1124")
        super_admin_response = self.client.delete(
            f"/api/auth/users/{super_admin['id']}",
            headers=self.auth_headers(admin_token),
        )
        self.assertEqual(super_admin_response.status_code, 403)
        self.assertEqual(super_admin_response.json()["detail"]["code"], "SUPER_ADMIN_PROTECTED")

        limited_admin_token = self.register_admin_and_login("delete.limited.admin", "member-password")
        create_response = self.client.post(
            "/api/auth/users",
            json={
                "username": "delete.blocked",
                "password": "delete-password",
                "display_name": "Delete Blocked",
                "role_codes": ["member"],
            },
            headers=self.auth_headers(admin_token),
        )
        self.assertEqual(create_response.status_code, 200)
        user_id = create_response.json()["user"]["id"]

        blocked_response = self.client.delete(
            f"/api/auth/users/{user_id}",
            headers=self.auth_headers(limited_admin_token),
        )
        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_response.json()["detail"]["code"], "PERMISSION_DENIED")
        self.assertIsNotNone(AuthRepository.get_user_by_id(user_id))

    def test_super_admin_can_create_update_and_delete_custom_role(self):
        token = self.login("lina1124", "initial-secret")

        create_response = self.client.post(
            "/api/auth/roles",
            json={
                "code": "stock.viewer",
                "name": "Stock Viewer",
                "description": "Can view inventory",
                "permission_codes": ["dashboard:view", "inventory:view"],
            },
            headers=self.auth_headers(token),
        )

        self.assertEqual(create_response.status_code, 200)
        role = create_response.json()["role"]
        self.assertFalse(role["is_system"])
        self.assertEqual(role["permission_codes"], ["dashboard:view", "inventory:view"])

        update_response = self.client.put(
            f"/api/auth/roles/{role['id']}",
            json={
                "name": "Stock Operator",
                "description": "Can view and update inventory",
                "permission_codes": ["dashboard:view", "inventory:view", "inventory:update"],
            },
            headers=self.auth_headers(token),
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertIn("inventory:update", update_response.json()["role"]["permission_codes"])

        delete_response = self.client.delete(f"/api/auth/roles/{role['id']}", headers=self.auth_headers(token))
        self.assertEqual(delete_response.status_code, 200)
        self.assertTrue(delete_response.json()["success"])

    def test_system_role_delete_is_rejected(self):
        token = self.login("lina1124", "initial-secret")
        roles_response = self.client.get("/api/auth/roles", headers=self.auth_headers(token))
        member_role = next(role for role in roles_response.json()["roles"] if role["code"] == "member")

        response = self.client.delete(f"/api/auth/roles/{member_role['id']}", headers=self.auth_headers(token))

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "SYSTEM_ROLE_PROTECTED")

    def test_role_in_use_delete_is_rejected(self):
        token = self.login("lina1124", "initial-secret")
        create_role_response = self.client.post(
            "/api/auth/roles",
            json={
                "code": "temporary.viewer",
                "name": "Temporary Viewer",
                "description": "",
                "permission_codes": ["dashboard:view"],
            },
            headers=self.auth_headers(token),
        )
        role = create_role_response.json()["role"]
        create_user_response = self.client.post(
            "/api/auth/users",
            json={
                "username": "role.bound",
                "password": "role-bound-password",
                "display_name": "Role Bound",
                "role_codes": ["temporary.viewer"],
            },
            headers=self.auth_headers(token),
        )
        self.assertEqual(create_user_response.status_code, 200)

        delete_response = self.client.delete(f"/api/auth/roles/{role['id']}", headers=self.auth_headers(token))

        self.assertEqual(delete_response.status_code, 409)
        self.assertEqual(delete_response.json()["detail"]["code"], "ROLE_IN_USE")

    def test_admin_without_role_create_permission_cannot_create_role(self):
        token = self.register_admin_and_login("role.limited.admin", "member-password")

        response = self.client.post(
            "/api/auth/roles",
            json={"code": "blocked.role", "name": "Blocked Role", "description": "", "permission_codes": []},
            headers=self.auth_headers(token),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["code"], "PERMISSION_DENIED")

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
    def count_rows(table_name: str, user_id: int) -> int:
        return int(store.query_one(f"SELECT COUNT(*) AS count FROM {table_name} WHERE user_id = ?", (user_id,))["count"])

    @staticmethod
    def auth_headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    unittest.main()
