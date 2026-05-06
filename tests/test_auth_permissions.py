import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException

import app.db.store as store
from app.db.auth_repository import AuthRepository
from backend.auth.dependencies import require_permission
from backend.models.auth_schemas import AuthUserResponse
from backend.services.auth_service import AuthContext, AuthService


class AuthPermissionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "auth-permissions-test.db")
        store._connection = None

        self.env_patch = patch.dict(
            os.environ,
            {
                "SEED_SUPER_ADMIN_USERNAME": "lina1124",
                "SEED_SUPER_ADMIN_PASSWORD": "initial-secret",
                "SEED_SUPER_ADMIN_FORCE_CHANGE_PASSWORD": "true",
            },
            clear=False,
        )
        self.env_patch.start()
        store.init_database()
        self.auth_service = AuthService()

    def tearDown(self):
        self.env_patch.stop()
        store.close_connection()
        store.DB_DIR = self.original_db_dir
        store.DB_PATH = self.original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def test_member_effective_permissions_apply_allow_and_deny_overrides(self):
        user = self.auth_service.register(username="member.one", password="member-password")
        base_permissions = set(user.permissions)
        self.assertIn("dashboard:view", base_permissions)
        self.assertIn("permission_request:create", base_permissions)
        self.assertNotIn("inventory:view", base_permissions)

        AuthRepository.upsert_user_permission_override(
            user_id=user.id,
            permission_code="inventory:view",
            effect="allow",
            reason="temporary read access",
        )
        AuthRepository.upsert_user_permission_override(
            user_id=user.id,
            permission_code="permission_request:create",
            effect="deny",
            reason="freeze requests",
        )

        refreshed_user = self.auth_service.build_user_response(AuthRepository.get_user_by_id(user.id))
        effective_permissions = set(refreshed_user.permissions)
        self.assertIn("dashboard:view", effective_permissions)
        self.assertIn("inventory:view", effective_permissions)
        self.assertNotIn("permission_request:create", effective_permissions)

    def test_permission_override_update_and_delete_recompute_effective_permissions(self):
        user = self.auth_service.register(username="member.two", password="member-password")

        AuthRepository.upsert_user_permission_override(
            user_id=user.id,
            permission_code="inventory:view",
            effect="allow",
            reason="grant",
        )
        self.assertIn(
            "inventory:view",
            self.auth_service.build_user_response(AuthRepository.get_user_by_id(user.id)).permissions,
        )

        AuthRepository.upsert_user_permission_override(
            user_id=user.id,
            permission_code="inventory:view",
            effect="deny",
            reason="revoke grant",
        )
        self.assertNotIn(
            "inventory:view",
            self.auth_service.build_user_response(AuthRepository.get_user_by_id(user.id)).permissions,
        )

        AuthRepository.delete_user_permission_override(user_id=user.id, permission_code="inventory:view")
        self.assertNotIn(
            "inventory:view",
            self.auth_service.build_user_response(AuthRepository.get_user_by_id(user.id)).permissions,
        )

    def test_super_admin_keeps_all_permissions_even_with_deny_override(self):
        super_admin = AuthRepository.get_user_by_username("lina1124")
        self.assertIsNotNone(super_admin)
        permission_count = len(AuthRepository.list_all_permission_codes())

        AuthRepository.upsert_user_permission_override(
            user_id=super_admin["id"],
            permission_code="dashboard:view",
            effect="deny",
            reason="should not reduce super admin",
        )

        user = self.auth_service.build_user_response(AuthRepository.get_user_by_id(super_admin["id"]))
        self.assertTrue(user.is_super_admin)
        self.assertIn("dashboard:view", user.permissions)
        self.assertEqual(len(user.permissions), permission_count)

    def test_require_permission_dependency_allows_and_rejects_by_effective_permissions(self):
        context = AuthContext(
            session_id=1,
            user_id=10,
            user=AuthUserResponse(
                id=10,
                username="member",
                display_name="member",
                roles=["member"],
                permissions=["dashboard:view"],
            ),
        )

        allowed_dependency = require_permission("dashboard:view")
        denied_dependency = require_permission("inventory:view")

        self.assertEqual(allowed_dependency(context), context)
        with self.assertRaises(HTTPException) as error:
            denied_dependency(context)
        self.assertEqual(error.exception.status_code, 403)
        self.assertEqual(error.exception.detail["code"], "PERMISSION_DENIED")


if __name__ == "__main__":
    unittest.main()
