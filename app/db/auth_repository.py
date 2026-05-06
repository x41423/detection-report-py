from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from app.db.store import get_connection, query, query_one, run


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _device_fingerprint(user_agent: str, ip_address: str) -> str:
    payload = f"{(user_agent or '').strip()}\n{(ip_address or '').strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_bool(value: Any) -> bool:
    return bool(int(value)) if isinstance(value, int | str) else bool(value)


class AuthRepository:
    @staticmethod
    def get_user_by_username(username: str) -> dict | None:
        return query_one("SELECT * FROM auth_users WHERE username = ?", (username,))

    @staticmethod
    def get_user_by_id(user_id: int) -> dict | None:
        return query_one("SELECT * FROM auth_users WHERE id = ?", (user_id,))

    @staticmethod
    def create_user_with_role(
        *,
        username: str,
        display_name: str,
        password_hash: str,
        password_salt: str,
        role_code: str,
    ) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                INSERT INTO auth_users (
                    username,
                    display_name,
                    password_hash,
                    password_salt,
                    is_active,
                    is_super_admin,
                    must_change_password,
                    password_changed_at
                )
                VALUES (?, ?, ?, ?, 1, 0, 0, ?)
                """,
                (username, display_name, password_hash, password_salt, _utc_now_iso()),
            )
            user_id = cursor.lastrowid
            role = cursor.execute("SELECT id FROM auth_roles WHERE code = ?", (role_code,)).fetchone()
            if role is None:
                raise ValueError(f"Role not found: {role_code}")
            cursor.execute(
                "INSERT OR IGNORE INTO auth_user_roles (user_id, role_id) VALUES (?, ?)",
                (user_id, role["id"]),
            )
            conn.commit()
            return AuthRepository.get_user_by_id(int(user_id))
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def create_managed_user(
        *,
        username: str,
        display_name: str,
        password_hash: str,
        password_salt: str,
        role_codes: list[str],
    ) -> dict:
        role_rows = AuthRepository._role_rows_for_codes(role_codes)
        if len(role_rows) != len(role_codes):
            raise ValueError("Invalid role code")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                INSERT INTO auth_users (
                    username,
                    display_name,
                    password_hash,
                    password_salt,
                    is_active,
                    is_super_admin,
                    must_change_password,
                    password_changed_at
                )
                VALUES (?, ?, ?, ?, 1, 0, 0, ?)
                """,
                (username, display_name, password_hash, password_salt, _utc_now_iso()),
            )
            user_id = int(cursor.lastrowid)
            for role in role_rows:
                cursor.execute(
                    "INSERT OR IGNORE INTO auth_user_roles (user_id, role_id) VALUES (?, ?)",
                    (user_id, role["id"]),
                )
            conn.commit()
            return AuthRepository.get_user_by_id(user_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def update_managed_user(
        *,
        user_id: int,
        display_name: str | None,
        role_codes: list[str] | None,
        is_active: bool | None,
    ) -> dict | None:
        target = AuthRepository.get_user_by_id(user_id)
        if target is None:
            return None

        role_rows: list[dict] | None = None
        if role_codes is not None:
            role_rows = AuthRepository._role_rows_for_codes(role_codes)
            if len(role_rows) != len(role_codes):
                raise ValueError("Invalid role code")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            if display_name is not None:
                cursor.execute(
                    "UPDATE auth_users SET display_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (display_name, user_id),
                )
            if is_active is not None:
                cursor.execute(
                    "UPDATE auth_users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (1 if is_active else 0, user_id),
                )
            if role_rows is not None:
                cursor.execute("DELETE FROM auth_user_roles WHERE user_id = ?", (user_id,))
                for role in role_rows:
                    cursor.execute(
                        "INSERT OR IGNORE INTO auth_user_roles (user_id, role_id) VALUES (?, ?)",
                        (user_id, role["id"]),
                    )
            conn.commit()
            return AuthRepository.get_user_by_id(user_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def list_users() -> list[dict]:
        return query(
            """
            SELECT u.*,
                   (
                       SELECT COUNT(*)
                       FROM auth_sessions s
                       WHERE s.user_id = u.id AND s.revoked_at IS NULL
                   ) AS active_session_count
            FROM auth_users u
            ORDER BY u.id ASC
            """
        )

    @staticmethod
    def record_login_failure(user_id: int) -> None:
        run(
            """
            UPDATE auth_users
            SET failed_login_count = COALESCE(failed_login_count, 0) + 1,
                last_failed_login_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (_utc_now_iso(), user_id),
        )

    @staticmethod
    def record_login_success(user_id: int) -> None:
        now = _utc_now_iso()
        run(
            """
            UPDATE auth_users
            SET failed_login_count = 0,
                locked_until = NULL,
                last_failed_login_at = NULL,
                last_login_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (now, user_id),
        )

    @staticmethod
    def get_device_by_fingerprint(*, user_id: int, user_agent: str, ip_address: str) -> dict | None:
        fingerprint = _device_fingerprint(user_agent, ip_address)
        return query_one(
            """
            SELECT *
            FROM auth_devices
            WHERE user_id = ? AND device_fingerprint = ?
            """,
            (user_id, fingerprint),
        )

    @staticmethod
    def count_active_devices_for_user(user_id: int) -> int:
        row = query_one("SELECT COUNT(*) AS count FROM auth_devices WHERE user_id = ? AND is_revoked = 0", (user_id,))
        return int((row or {}).get("count") or 0)

    @staticmethod
    def create_pending_login(
        *,
        user_id: int,
        pending_token_hash: str,
        ip_address: str,
        user_agent: str,
        device_name: str,
        expires_at: str,
    ) -> dict:
        pending_id = run(
            """
            INSERT INTO auth_pending_logins (
                user_id,
                pending_token_hash,
                ip_address,
                user_agent,
                device_name,
                expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, pending_token_hash, ip_address, user_agent, device_name, expires_at),
        )
        return query_one("SELECT * FROM auth_pending_logins WHERE id = ?", (pending_id,))

    @staticmethod
    def get_pending_login_by_token_hash(token_hash: str) -> dict | None:
        return query_one(
            "SELECT * FROM auth_pending_logins WHERE pending_token_hash = ?",
            (token_hash,),
        )

    @staticmethod
    def create_session(
        *,
        user_id: int,
        access_token_hash: str,
        refresh_token_hash: str,
        access_expires_at: str,
        refresh_expires_at: str,
        user_agent: str,
        ip_address: str,
        device_name: str,
    ) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            device_id = AuthRepository._ensure_device(
                cursor=cursor,
                user_id=user_id,
                user_agent=user_agent,
                ip_address=ip_address,
                device_name=device_name,
            )
            cursor.execute(
                """
                INSERT INTO auth_sessions (
                    user_id,
                    device_id,
                    access_token_hash,
                    refresh_token_hash,
                    access_expires_at,
                    refresh_expires_at,
                    ip_address,
                    user_agent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    device_id,
                    access_token_hash,
                    refresh_token_hash,
                    access_expires_at,
                    refresh_expires_at,
                    ip_address,
                    user_agent,
                ),
            )
            session_id = int(cursor.lastrowid)
            conn.commit()
            return query_one("SELECT * FROM auth_sessions WHERE id = ?", (session_id,))
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def create_session_replacing_device(
        *,
        pending_login_id: int,
        replace_device_id: int,
        access_token_hash: str,
        refresh_token_hash: str,
        access_expires_at: str,
        refresh_expires_at: str,
    ) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            pending = cursor.execute(
                "SELECT * FROM auth_pending_logins WHERE id = ?",
                (pending_login_id,),
            ).fetchone()
            if pending is None:
                raise ValueError("Pending login not found")
            device = cursor.execute(
                "SELECT * FROM auth_devices WHERE id = ? AND user_id = ?",
                (replace_device_id, pending["user_id"]),
            ).fetchone()
            if device is None:
                raise ValueError("Device not found")

            AuthRepository._revoke_device_sessions(cursor, replace_device_id, "device_replaced")
            fingerprint = _device_fingerprint(pending["user_agent"], pending["ip_address"])
            now = _utc_now_iso()
            cursor.execute(
                """
                UPDATE auth_devices
                SET device_name = ?,
                    device_fingerprint = ?,
                    user_agent = ?,
                    ip_address = ?,
                    last_active_at = ?,
                    is_revoked = 0,
                    revoked_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    pending["device_name"] or device["device_name"],
                    fingerprint,
                    pending["user_agent"],
                    pending["ip_address"],
                    now,
                    replace_device_id,
                ),
            )
            cursor.execute(
                """
                INSERT INTO auth_sessions (
                    user_id,
                    device_id,
                    access_token_hash,
                    refresh_token_hash,
                    access_expires_at,
                    refresh_expires_at,
                    ip_address,
                    user_agent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pending["user_id"],
                    replace_device_id,
                    access_token_hash,
                    refresh_token_hash,
                    access_expires_at,
                    refresh_expires_at,
                    pending["ip_address"],
                    pending["user_agent"],
                ),
            )
            session_id = int(cursor.lastrowid)
            cursor.execute(
                "UPDATE auth_pending_logins SET used_at = ? WHERE id = ?",
                (now, pending_login_id),
            )
            conn.commit()
            return query_one("SELECT * FROM auth_sessions WHERE id = ?", (session_id,))
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def rotate_session_tokens(
        *,
        session_id: int,
        access_token_hash: str,
        refresh_token_hash: str,
        access_expires_at: str,
        refresh_expires_at: str,
        ip_address: str,
        user_agent: str,
    ) -> dict:
        run(
            """
            UPDATE auth_sessions
            SET access_token_hash = ?,
                refresh_token_hash = ?,
                access_expires_at = ?,
                refresh_expires_at = ?,
                ip_address = ?,
                user_agent = ?,
                last_active_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                access_token_hash,
                refresh_token_hash,
                access_expires_at,
                refresh_expires_at,
                ip_address,
                user_agent,
                session_id,
            ),
        )
        return query_one("SELECT * FROM auth_sessions WHERE id = ?", (session_id,))

    @staticmethod
    def get_active_session_by_access_token_hash(token_hash: str) -> dict | None:
        return query_one(
            """
            SELECT s.*, u.username, u.display_name, u.is_active, u.is_super_admin, u.must_change_password
            FROM auth_sessions s
            JOIN auth_users u ON u.id = s.user_id
            JOIN auth_devices d ON d.id = s.device_id
            WHERE s.access_token_hash = ?
              AND s.revoked_at IS NULL
              AND d.is_revoked = 0
            """,
            (token_hash,),
        )

    @staticmethod
    def get_active_session_by_refresh_token_hash(token_hash: str) -> dict | None:
        return query_one(
            """
            SELECT s.*, u.username, u.display_name, u.is_active, u.is_super_admin, u.must_change_password
            FROM auth_sessions s
            JOIN auth_users u ON u.id = s.user_id
            JOIN auth_devices d ON d.id = s.device_id
            WHERE s.refresh_token_hash = ?
              AND s.revoked_at IS NULL
              AND d.is_revoked = 0
            """,
            (token_hash,),
        )

    @staticmethod
    def touch_session(session_id: int) -> None:
        run(
            """
            UPDATE auth_sessions
            SET last_active_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (session_id,),
        )

    @staticmethod
    def revoke_session(session_id: int, reason: str) -> None:
        run(
            """
            UPDATE auth_sessions
            SET revoked_at = ?,
                revoke_reason = ?,
                last_active_at = CURRENT_TIMESTAMP
            WHERE id = ? AND revoked_at IS NULL
            """,
            (_utc_now_iso(), reason, session_id),
        )

    @staticmethod
    def get_device_id_for_session(session_id: int) -> int | None:
        row = query_one("SELECT device_id FROM auth_sessions WHERE id = ?", (session_id,))
        return int(row["device_id"]) if row and row.get("device_id") is not None else None

    @staticmethod
    def list_devices_for_user(user_id: int, current_device_id: int | None = None) -> list[dict]:
        rows = query(
            """
            SELECT d.*,
                   (
                       SELECT COUNT(*)
                       FROM auth_sessions s
                       WHERE s.device_id = d.id AND s.revoked_at IS NULL
                   ) AS active_session_count
            FROM auth_devices d
            WHERE d.user_id = ?
            ORDER BY d.last_active_at DESC, d.id DESC
            """,
            (user_id,),
        )
        for row in rows:
            row["is_current"] = int(current_device_id is not None and int(row["id"]) == int(current_device_id))
        return rows

    @staticmethod
    def rename_device(*, user_id: int, device_id: int, device_name: str, current_device_id: int | None) -> dict | None:
        updated = run(
            """
            UPDATE auth_devices
            SET device_name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (device_name, device_id, user_id),
        )
        if updated is None:
            pass
        row = AuthRepository._device_with_session_count(device_id, current_device_id)
        if row is None or int(row["user_id"]) != int(user_id):
            return None
        return row

    @staticmethod
    def revoke_device(*, user_id: int, device_id: int, reason: str, current_device_id: int | None) -> dict | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            device = cursor.execute(
                "SELECT * FROM auth_devices WHERE id = ? AND user_id = ?",
                (device_id, user_id),
            ).fetchone()
            if device is None:
                conn.rollback()
                return None
            now = _utc_now_iso()
            cursor.execute(
                """
                UPDATE auth_devices
                SET is_revoked = 1,
                    revoked_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (now, device_id),
            )
            AuthRepository._revoke_device_sessions(cursor, device_id, reason)
            conn.commit()
            return AuthRepository._device_with_session_count(device_id, current_device_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def list_all_permissions() -> list[dict]:
        return query(
            """
            SELECT *
            FROM auth_permissions
            ORDER BY module ASC, code ASC
            """
        )

    @staticmethod
    def list_all_permission_codes() -> list[str]:
        return [row["code"] for row in AuthRepository.list_all_permissions()]

    @staticmethod
    def get_permission_by_code(permission_code: str) -> dict | None:
        return query_one("SELECT * FROM auth_permissions WHERE code = ?", (permission_code,))

    @staticmethod
    def list_roles_for_user(user_id: int) -> list[str]:
        rows = query(
            """
            SELECT r.code
            FROM auth_user_roles ur
            JOIN auth_roles r ON r.id = ur.role_id
            WHERE ur.user_id = ?
            ORDER BY ur.id ASC, r.id ASC
            """,
            (user_id,),
        )
        return [row["code"] for row in rows]

    @staticmethod
    def list_permissions_for_user(user_id: int) -> list[str]:
        user = AuthRepository.get_user_by_id(user_id)
        if user is None:
            return []
        if _normalize_bool(user.get("is_super_admin")):
            return AuthRepository.list_all_permission_codes()

        role_rows = query(
            """
            SELECT DISTINCT p.code
            FROM auth_user_roles ur
            JOIN auth_role_permissions rp ON rp.role_id = ur.role_id
            JOIN auth_permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = ?
            ORDER BY p.code ASC
            """,
            (user_id,),
        )
        permissions = {row["code"] for row in role_rows}
        overrides = query(
            """
            SELECT p.code, o.effect
            FROM auth_user_permission_overrides o
            JOIN auth_permissions p ON p.id = o.permission_id
            WHERE o.user_id = ?
            """,
            (user_id,),
        )
        for row in overrides:
            if row["effect"] == "allow":
                permissions.add(row["code"])
            elif row["effect"] == "deny":
                permissions.discard(row["code"])
        return sorted(permissions)

    @staticmethod
    def upsert_user_permission_override(*, user_id: int, permission_code: str, effect: str, reason: str) -> None:
        permission = AuthRepository.get_permission_by_code(permission_code)
        if permission is None:
            raise ValueError("Permission not found")
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            existing = cursor.execute(
                """
                SELECT id
                FROM auth_user_permission_overrides
                WHERE user_id = ? AND permission_id = ?
                """,
                (user_id, permission["id"]),
            ).fetchone()
            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO auth_user_permission_overrides (user_id, permission_id, effect, reason)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, permission["id"], effect, reason),
                )
            else:
                cursor.execute(
                    """
                    UPDATE auth_user_permission_overrides
                    SET effect = ?, reason = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (effect, reason, existing["id"]),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def delete_user_permission_override(*, user_id: int, permission_code: str) -> None:
        permission = AuthRepository.get_permission_by_code(permission_code)
        if permission is None:
            return
        run(
            "DELETE FROM auth_user_permission_overrides WHERE user_id = ? AND permission_id = ?",
            (user_id, permission["id"]),
        )

    @staticmethod
    def create_permission_request(*, user_id: int, permission_code: str, reason: str) -> dict:
        permission = AuthRepository.get_permission_by_code(permission_code)
        permission_id = permission["id"] if permission else None
        request_id = run(
            """
            INSERT INTO auth_permission_requests (user_id, permission_id, permission_code, reason, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (user_id, permission_id, permission_code, reason),
        )
        return AuthRepository._permission_request_with_joins(int(request_id))

    @staticmethod
    def list_permission_requests_for_user(user_id: int) -> list[dict]:
        return AuthRepository._permission_request_rows("WHERE pr.user_id = ?", (user_id,))

    @staticmethod
    def list_permission_requests(status: str | None = None) -> list[dict]:
        if status:
            return AuthRepository._permission_request_rows("WHERE pr.status = ?", (status,))
        return AuthRepository._permission_request_rows("", ())

    @staticmethod
    def review_permission_request(
        *,
        request_id: int,
        reviewer_id: int,
        status: str,
        review_comment: str,
    ) -> dict | None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            request_row = cursor.execute(
                "SELECT * FROM auth_permission_requests WHERE id = ?",
                (request_id,),
            ).fetchone()
            if request_row is None:
                conn.rollback()
                return None
            if request_row["status"] != "pending":
                raise ValueError("Permission request is not pending")

            reviewed_at = _utc_now_iso()
            cursor.execute(
                """
                UPDATE auth_permission_requests
                SET status = ?, reviewer_id = ?, review_comment = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (status, reviewer_id, review_comment, reviewed_at, request_id),
            )
            if status == "approved":
                permission_code = request_row["permission_code"]
                permission = AuthRepository.get_permission_by_code(permission_code)
                if permission is not None:
                    existing = cursor.execute(
                        """
                        SELECT id
                        FROM auth_user_permission_overrides
                        WHERE user_id = ? AND permission_id = ?
                        """,
                        (request_row["user_id"], permission["id"]),
                    ).fetchone()
                    reason = review_comment or request_row["reason"] or "permission_request_approved"
                    if existing is None:
                        cursor.execute(
                            """
                            INSERT INTO auth_user_permission_overrides (user_id, permission_id, effect, reason)
                            VALUES (?, ?, 'allow', ?)
                            """,
                            (request_row["user_id"], permission["id"], reason),
                        )
                    else:
                        cursor.execute(
                            """
                            UPDATE auth_user_permission_overrides
                            SET effect = 'allow', reason = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (reason, existing["id"]),
                        )
            conn.commit()
            return AuthRepository._permission_request_with_joins(request_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def get_role_by_code(role_code: str) -> dict | None:
        return query_one("SELECT * FROM auth_roles WHERE code = ?", (role_code,))

    @staticmethod
    def get_role_by_id(role_id: int) -> dict | None:
        role = query_one("SELECT * FROM auth_roles WHERE id = ?", (role_id,))
        if role is None:
            return None
        return AuthRepository._role_response_row(role)

    @staticmethod
    def list_roles() -> list[dict]:
        rows = query("SELECT * FROM auth_roles ORDER BY id ASC")
        return [AuthRepository._role_response_row(row) for row in rows]

    @staticmethod
    def create_role(*, code: str, name: str, description: str, permission_codes: list[str]) -> dict:
        permission_rows = AuthRepository._permission_rows_for_codes(permission_codes)
        if len(permission_rows) != len(permission_codes):
            raise ValueError("Invalid permission code")
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute(
                """
                INSERT INTO auth_roles (code, name, description, is_system)
                VALUES (?, ?, ?, 0)
                """,
                (code, name, description),
            )
            role_id = int(cursor.lastrowid)
            for permission in permission_rows:
                cursor.execute(
                    "INSERT OR IGNORE INTO auth_role_permissions (role_id, permission_id) VALUES (?, ?)",
                    (role_id, permission["id"]),
                )
            conn.commit()
            return AuthRepository.get_role_by_id(role_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def update_role(*, role_id: int, name: str, description: str, permission_codes: list[str]) -> dict | None:
        permission_rows = AuthRepository._permission_rows_for_codes(permission_codes)
        if len(permission_rows) != len(permission_codes):
            raise ValueError("Invalid permission code")
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            target = cursor.execute("SELECT id FROM auth_roles WHERE id = ?", (role_id,)).fetchone()
            if target is None:
                conn.rollback()
                return None
            cursor.execute(
                """
                UPDATE auth_roles
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (name, description, role_id),
            )
            cursor.execute("DELETE FROM auth_role_permissions WHERE role_id = ?", (role_id,))
            for permission in permission_rows:
                cursor.execute(
                    "INSERT OR IGNORE INTO auth_role_permissions (role_id, permission_id) VALUES (?, ?)",
                    (role_id, permission["id"]),
                )
            conn.commit()
            return AuthRepository.get_role_by_id(role_id)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def delete_role(role_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            target = cursor.execute("SELECT id FROM auth_roles WHERE id = ?", (role_id,)).fetchone()
            if target is None:
                conn.rollback()
                return False
            cursor.execute("DELETE FROM auth_role_permissions WHERE role_id = ?", (role_id,))
            cursor.execute("DELETE FROM auth_user_roles WHERE role_id = ?", (role_id,))
            cursor.execute("DELETE FROM auth_roles WHERE id = ?", (role_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def create_audit_log(
        *,
        actor_user_id: int | None,
        target_user_id: int | None,
        action: str,
        module: str,
        description: str,
        ip_address: str,
        user_agent: str,
        result: str,
    ) -> None:
        run(
            """
            INSERT INTO auth_audit_logs (
                actor_user_id,
                target_user_id,
                action,
                module,
                description,
                ip_address,
                user_agent,
                result
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (actor_user_id, target_user_id, action, module, description, ip_address, user_agent, result),
        )

    @staticmethod
    def list_audit_logs(
        *,
        limit: int,
        module: str | None,
        action: str | None,
        result: str | None,
        actor_user_id: int | None,
        target_user_id: int | None,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[Any] = []
        if module is not None:
            clauses.append("l.module = ?")
            params.append(module)
        if action is not None:
            clauses.append("l.action = ?")
            params.append(action)
        if result is not None:
            clauses.append("l.result = ?")
            params.append(result)
        if actor_user_id is not None:
            clauses.append("l.actor_user_id = ?")
            params.append(actor_user_id)
        if target_user_id is not None:
            clauses.append("l.target_user_id = ?")
            params.append(target_user_id)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        return query(
            f"""
            SELECT l.*,
                   au.username AS actor_username,
                   au.display_name AS actor_display_name,
                   tu.username AS target_username,
                   tu.display_name AS target_display_name
            FROM auth_audit_logs l
            LEFT JOIN auth_users au ON au.id = l.actor_user_id
            LEFT JOIN auth_users tu ON tu.id = l.target_user_id
            {where_sql}
            ORDER BY l.id DESC
            LIMIT ?
            """,
            tuple(params),
        )

    @staticmethod
    def _role_rows_for_codes(role_codes: list[str]) -> list[dict]:
        rows: list[dict] = []
        for code in role_codes:
            row = AuthRepository.get_role_by_code(code)
            if row is not None:
                rows.append(row)
        return rows

    @staticmethod
    def _permission_rows_for_codes(permission_codes: list[str]) -> list[dict]:
        rows: list[dict] = []
        for code in permission_codes:
            row = AuthRepository.get_permission_by_code(code)
            if row is not None:
                rows.append(row)
        return rows

    @staticmethod
    def _ensure_device(
        *,
        cursor,
        user_id: int,
        user_agent: str,
        ip_address: str,
        device_name: str,
    ) -> int:
        fingerprint = _device_fingerprint(user_agent, ip_address)
        now = _utc_now_iso()
        device = cursor.execute(
            """
            SELECT *
            FROM auth_devices
            WHERE user_id = ? AND device_fingerprint = ?
            """,
            (user_id, fingerprint),
        ).fetchone()
        if device is None:
            cursor.execute(
                """
                INSERT INTO auth_devices (
                    user_id,
                    device_name,
                    device_fingerprint,
                    user_agent,
                    ip_address,
                    first_login_at,
                    last_active_at,
                    is_revoked
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (user_id, device_name, fingerprint, user_agent, ip_address, now, now),
            )
            return int(cursor.lastrowid)
        cursor.execute(
            """
            UPDATE auth_devices
            SET device_name = ?,
                user_agent = ?,
                ip_address = ?,
                last_active_at = ?,
                is_revoked = 0,
                revoked_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (device_name or device["device_name"], user_agent, ip_address, now, device["id"]),
        )
        return int(device["id"])

    @staticmethod
    def _revoke_device_sessions(cursor, device_id: int, reason: str) -> None:
        cursor.execute(
            """
            UPDATE auth_sessions
            SET revoked_at = ?,
                revoke_reason = ?,
                last_active_at = CURRENT_TIMESTAMP
            WHERE device_id = ? AND revoked_at IS NULL
            """,
            (_utc_now_iso(), reason, device_id),
        )

    @staticmethod
    def _device_with_session_count(device_id: int, current_device_id: int | None) -> dict | None:
        row = query_one(
            """
            SELECT d.*,
                   (
                       SELECT COUNT(*)
                       FROM auth_sessions s
                       WHERE s.device_id = d.id AND s.revoked_at IS NULL
                   ) AS active_session_count
            FROM auth_devices d
            WHERE d.id = ?
            """,
            (device_id,),
        )
        if row is None:
            return None
        row["is_current"] = int(current_device_id is not None and int(row["id"]) == int(current_device_id))
        return row

    @staticmethod
    def _permission_request_rows(where_sql: str, params: tuple[Any, ...]) -> list[dict]:
        return query(
            f"""
            SELECT pr.*,
                   u.username,
                   u.display_name,
                   p.name AS permission_name,
                   p.module AS permission_module,
                   reviewer.username AS reviewer_username,
                   reviewer.display_name AS reviewer_display_name
            FROM auth_permission_requests pr
            JOIN auth_users u ON u.id = pr.user_id
            LEFT JOIN auth_permissions p ON p.id = pr.permission_id
            LEFT JOIN auth_users reviewer ON reviewer.id = pr.reviewer_id
            {where_sql}
            ORDER BY pr.id DESC
            """,
            params,
        )

    @staticmethod
    def _permission_request_with_joins(request_id: int) -> dict | None:
        rows = AuthRepository._permission_request_rows("WHERE pr.id = ?", (request_id,))
        return rows[0] if rows else None

    @staticmethod
    def _role_response_row(role: dict) -> dict:
        permission_rows = query(
            """
            SELECT p.code
            FROM auth_role_permissions rp
            JOIN auth_permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = ?
            ORDER BY p.code ASC
            """,
            (role["id"],),
        )
        user_count_row = query_one(
            "SELECT COUNT(*) AS count FROM auth_user_roles WHERE role_id = ?",
            (role["id"],),
        )
        return {
            **role,
            "permission_codes": [row["code"] for row in permission_rows],
            "user_count": int((user_count_row or {}).get("count") or 0),
        }
