import os
import sqlite3
import tempfile
import unittest

import app.db.store as store


AUTH_TABLES = {
    "schema_migrations",
    "auth_users",
    "auth_roles",
    "auth_permissions",
    "auth_user_roles",
    "auth_role_permissions",
    "auth_user_permission_overrides",
    "auth_permission_requests",
    "auth_devices",
    "auth_sessions",
    "auth_refresh_token_grace",
    "auth_pending_logins",
    "auth_audit_logs",
}


class AuthSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_dir = store.DB_DIR
        self.original_db_path = store.DB_PATH
        store.close_connection()
        store.DB_DIR = self.temp_dir.name
        store.DB_PATH = os.path.join(self.temp_dir.name, "auth-schema-test.db")
        store._connection = None

    def tearDown(self):
        store.close_connection()
        store.DB_DIR = self.original_db_dir
        store.DB_PATH = self.original_db_path
        store._connection = None
        self.temp_dir.cleanup()

    def test_init_database_creates_auth_tables_idempotently(self):
        store.init_database()
        store.init_database()

        tables = {
            row["name"]
            for row in store.query(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }
        migration = store.query_one(
            "SELECT version, name FROM schema_migrations WHERE version = ?",
            (1,),
        )

        self.assertTrue(AUTH_TABLES.issubset(tables))
        self.assertEqual(migration, {"version": 1, "name": "auth_core_schema"})

    def test_connection_enables_foreign_keys_and_wal(self):
        store.init_database()
        conn = store.get_connection()

        foreign_keys_enabled = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

        self.assertEqual(foreign_keys_enabled, 1)
        self.assertEqual(journal_mode.lower(), "wal")

    def test_auth_relationships_enforce_foreign_keys(self):
        store.init_database()
        conn = store.get_connection()

        user_id = store.run(
            """
            INSERT INTO auth_users (username, display_name, password_hash, password_salt)
            VALUES (?, ?, ?, ?)
            """,
            ("tester", "Tester", "hash", "salt"),
        )
        role = store.query_one("SELECT id FROM auth_roles WHERE code = ?", ("member",))
        store.run(
            """
            INSERT INTO auth_user_roles (user_id, role_id)
            VALUES (?, ?)
            """,
            (user_id, role["id"]),
        )

        with self.assertRaises(sqlite3.IntegrityError):
            store.run(
                """
                INSERT INTO auth_user_roles (user_id, role_id)
                VALUES (?, ?)
                """,
                (user_id, 9999),
            )

        conn.execute("DELETE FROM auth_users WHERE id = ?", (user_id,))
        conn.commit()

        remaining = store.query_one(
            "SELECT COUNT(*) AS count FROM auth_user_roles WHERE user_id = ?",
            (user_id,),
        )
        self.assertEqual(remaining["count"], 0)

    def test_pending_permission_request_is_unique_per_user_and_permission(self):
        store.init_database()

        user_id = store.run(
            """
            INSERT INTO auth_users (username, display_name, password_hash, password_salt)
            VALUES (?, ?, ?, ?)
            """,
            ("requester", "Requester", "hash", "salt"),
        )
        store.run(
            """
            INSERT INTO auth_permission_requests (user_id, permission_code, reason)
            VALUES (?, ?, ?)
            """,
            (user_id, "inventory:update", "Need to manage inventory"),
        )

        with self.assertRaises(sqlite3.IntegrityError):
            store.run(
                """
                INSERT INTO auth_permission_requests (user_id, permission_code, reason)
                VALUES (?, ?, ?)
                """,
                (user_id, "inventory:update", "Duplicate pending request"),
            )

        store.run(
            """
            UPDATE auth_permission_requests
            SET status = 'cancelled'
            WHERE user_id = ? AND permission_code = ?
            """,
            (user_id, "inventory:update"),
        )
        new_request_id = store.run(
            """
            INSERT INTO auth_permission_requests (user_id, permission_code, reason)
            VALUES (?, ?, ?)
            """,
            (user_id, "inventory:update", "Request again after cancellation"),
        )

        self.assertGreater(new_request_id, 0)


if __name__ == "__main__":
    unittest.main()
