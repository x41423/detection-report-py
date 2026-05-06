"""Reconstructed AuthService.

The original file was overwritten with unrelated content.  This rebuild
provides the public surface required by the rest of the backend (route
handlers, dependency injection, device/permission/user services) while
delegating persistence to :class:`AuthRepository`.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.db.auth_repository import AuthRepository
from backend.auth.passwords import generate_password_salt, hash_password, verify_password
from backend.models.auth_schemas import AuthUserResponse


_LOGGER = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(str(os.getenv(name) or default).strip() or default))
    except (TypeError, ValueError):
        return default


def _env_int_any(names: tuple[str, ...], default: int) -> int:
    """Return the first env-resolved positive int among ``names``.

    Lets us accept both the historical ``AUTH_*_TTL_*`` names and the newer
    ``AUTH_*_MINUTES`` / ``AUTH_*_DAYS`` aliases the test-suite (and several
    deployment manifests) expect.
    """
    for name in names:
        raw = os.getenv(name)
        if raw is None or str(raw).strip() == "":
            continue
        try:
            return max(1, int(str(raw).strip()))
        except (TypeError, ValueError):
            continue
    return default


# Resolved lazily so tests / deployments can override via env-patching at
# runtime (the values were previously frozen at import time).
def _access_token_ttl_min() -> int:
    return _env_int_any(("AUTH_ACCESS_TOKEN_MINUTES", "AUTH_ACCESS_TOKEN_TTL_MIN"), 30)


def _refresh_token_ttl_days() -> int:
    return _env_int_any(("AUTH_REFRESH_TOKEN_DAYS", "AUTH_REFRESH_TOKEN_TTL_DAYS"), 14)


def _pending_login_ttl_min() -> int:
    return _env_int_any(("AUTH_PENDING_LOGIN_MINUTES", "AUTH_PENDING_LOGIN_TTL_MIN"), 5)


def _max_active_devices_per_user() -> int:
    return _env_int_any(
        ("AUTH_MAX_DEVICES_PER_ACCOUNT", "AUTH_MAX_ACTIVE_DEVICES_PER_USER"), 3
    )


# Backwards-compatible module-level views (read at import time – still used
# by code that does not need the test-friendly runtime override).
ACCESS_TOKEN_TTL_MIN = _access_token_ttl_min()
REFRESH_TOKEN_TTL_DAYS = _refresh_token_ttl_days()
PENDING_LOGIN_TTL_MIN = _pending_login_ttl_min()
MAX_ACTIVE_DEVICES_PER_USER = _max_active_devices_per_user()
DEFAULT_REGISTRATION_ROLE = (os.getenv("AUTH_DEFAULT_REGISTRATION_ROLE") or "member").strip() or "member"


class AuthServiceError(RuntimeError):
    """Domain error carrying an HTTP status code and a stable error code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = int(status_code)
        self.code = code
        self.message = message


@dataclass(slots=True)
class AuthContext:
    session_id: int
    user_id: int
    user: AuthUserResponse


# ---------------------------------------------------------------------------
# helpers


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _utc_iso(dt: datetime) -> str:
    return dt.isoformat()


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _iso_to_utc(text: str) -> datetime | None:
    candidate = (text or "").strip()
    if not candidate:
        return None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_expired(iso_text: str) -> bool:
    parsed = _iso_to_utc(iso_text)
    if parsed is None:
        return False
    return parsed < _utc_now()


# ---------------------------------------------------------------------------
# service


class AuthService:
    def __init__(self, repository: AuthRepository | None = None):
        self.repository = repository or AuthRepository()

    # ---- registration -----------------------------------------------------

    def register(
        self,
        *,
        username: str,
        password: str,
        display_name: str | None = None,
    ) -> AuthUserResponse:
        normalized_username = (username or "").strip().lower()
        self._validate_username(normalized_username)
        self._validate_password(password)

        if self.repository.get_user_by_username(normalized_username):
            raise AuthServiceError(409, "USERNAME_EXISTS", "用户名已被注册")

        clean_display = (display_name or normalized_username).strip() or normalized_username
        salt = generate_password_salt()
        password_hash = hash_password(password, salt)
        try:
            user = self.repository.create_user_with_role(
                username=normalized_username,
                display_name=clean_display,
                password_hash=password_hash,
                password_salt=salt,
                role_code=DEFAULT_REGISTRATION_ROLE,
            )
        except ValueError as exc:
            raise AuthServiceError(500, "REGISTRATION_FAILED", "注册失败，默认角色不可用") from exc
        except Exception as exc:  # pragma: no cover - integrity edge cases
            _LOGGER.exception("Failed to register user %s", normalized_username)
            raise AuthServiceError(500, "REGISTRATION_FAILED", "注册失败，请稍后再试") from exc
        return self._hydrate_user_response(user)

    # ---- login ------------------------------------------------------------

    def login(
        self,
        *,
        username: str,
        password: str,
        user_agent: str,
        ip_address: str,
        device_name: str | None,
    ) -> dict:
        normalized_username = (username or "").strip().lower()
        user = self.repository.get_user_by_username(normalized_username)
        if not user:
            raise AuthServiceError(401, "INVALID_CREDENTIALS", "用户名或密码错误")
        if not _as_bool(user.get("is_active")):
            raise AuthServiceError(403, "ACCOUNT_DISABLED", "账号已被停用")

        if not verify_password(password, user["password_salt"], user["password_hash"]):
            try:
                self.repository.record_login_failure(int(user["id"]))
            except Exception:  # pragma: no cover
                _LOGGER.exception("Failed to record login failure")
            raise AuthServiceError(401, "INVALID_CREDENTIALS", "用户名或密码错误")

        try:
            self.repository.record_login_success(int(user["id"]))
        except Exception:  # pragma: no cover
            _LOGGER.exception("Failed to record login success")

        user_id = int(user["id"])
        clean_device_name = (device_name or "").strip() or "未命名设备"
        existing_device = self.repository.get_device_by_fingerprint(
            user_id=user_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        if existing_device is None and self.repository.count_active_devices_for_user(user_id) >= _max_active_devices_per_user():
            return self._build_pending_login_response(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                device_name=clean_device_name,
            )

        return self._create_session_and_response(
            user=user,
            user_agent=user_agent,
            ip_address=ip_address,
            device_name=clean_device_name,
        )

    def replace_device_login(
        self,
        *,
        pending_token: str,
        replace_device_id: int,
    ) -> dict:
        pending = self.repository.get_pending_login_by_token_hash(_token_hash(pending_token or ""))
        if not pending:
            raise AuthServiceError(400, "INVALID_PENDING_TOKEN", "临时登录凭证已失效，请重新登录")
        if pending.get("used_at"):
            raise AuthServiceError(400, "PENDING_TOKEN_USED", "临时登录凭证已使用")
        if _is_expired(str(pending.get("expires_at") or "")):
            raise AuthServiceError(401, "PENDING_LOGIN_EXPIRED", "临时登录凭证已过期，请重新登录")

        access_token = _new_token()
        refresh_token = _new_token()
        now = _utc_now()
        access_expires_at = _utc_iso(now + timedelta(minutes=_access_token_ttl_min()))
        refresh_expires_at = _utc_iso(now + timedelta(days=_refresh_token_ttl_days()))
        try:
            self.repository.create_session_replacing_device(
                pending_login_id=int(pending["id"]),
                replace_device_id=int(replace_device_id),
                access_token_hash=_token_hash(access_token),
                refresh_token_hash=_token_hash(refresh_token),
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at,
            )
        except ValueError as exc:
            raise AuthServiceError(400, "DEVICE_REPLACE_FAILED", str(exc) or "设备替换失败") from exc

        user = self.repository.get_user_by_id(int(pending["user_id"]))
        if not user:
            raise AuthServiceError(500, "USER_LOOKUP_FAILED", "用户数据异常")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_at": access_expires_at,
            "refresh_expires_at": refresh_expires_at,
            "user": self._hydrate_user_response(user),
        }

    # ---- session lifecycle -----------------------------------------------

    def refresh(
        self,
        *,
        refresh_token: str,
        user_agent: str,
        ip_address: str,
    ) -> dict:
        if not refresh_token:
            raise AuthServiceError(401, "REFRESH_REQUIRED", "缺少刷新凭证")
        session = self.repository.get_active_session_by_refresh_token_hash(_token_hash(refresh_token))
        if not session:
            raise AuthServiceError(401, "INVALID_REFRESH_TOKEN", "刷新凭证无效，请重新登录")
        if _is_expired(str(session.get("refresh_expires_at") or "")):
            try:
                self.repository.revoke_session(int(session["id"]), "refresh_expired")
            except Exception:  # pragma: no cover
                _LOGGER.exception("Failed to revoke expired session %s", session.get("id"))
            raise AuthServiceError(401, "REFRESH_TOKEN_EXPIRED", "刷新凭证已过期，请重新登录")
        if not _as_bool(session.get("is_active")):
            raise AuthServiceError(403, "ACCOUNT_DISABLED", "账号已被停用")

        new_access = _new_token()
        new_refresh = _new_token()
        now = _utc_now()
        access_expires_at = _utc_iso(now + timedelta(minutes=_access_token_ttl_min()))
        refresh_expires_at = _utc_iso(now + timedelta(days=_refresh_token_ttl_days()))
        self.repository.rotate_session_tokens(
            session_id=int(session["id"]),
            access_token_hash=_token_hash(new_access),
            refresh_token_hash=_token_hash(new_refresh),
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        user = self.repository.get_user_by_id(int(session["user_id"]))
        if not user:
            raise AuthServiceError(500, "USER_LOOKUP_FAILED", "用户数据异常")
        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_at": access_expires_at,
            "refresh_expires_at": refresh_expires_at,
            "user": self._hydrate_user_response(user),
        }

    def logout(self, *, session_id: int) -> None:
        try:
            self.repository.revoke_session(int(session_id), "user_logout")
        except Exception:  # pragma: no cover
            _LOGGER.exception("Failed to revoke session %s", session_id)

    def authenticate_access_token(self, access_token: str) -> AuthContext:
        if not access_token or not access_token.strip():
            raise AuthServiceError(401, "AUTH_REQUIRED", "请先登录")
        session = self.repository.get_active_session_by_access_token_hash(_token_hash(access_token.strip()))
        if not session:
            raise AuthServiceError(401, "INVALID_TOKEN", "登录凭证无效")
        if _is_expired(str(session.get("access_expires_at") or "")):
            raise AuthServiceError(401, "TOKEN_EXPIRED", "登录凭证已过期，请重新登录")
        if not _as_bool(session.get("is_active")):
            raise AuthServiceError(403, "ACCOUNT_DISABLED", "账号已被停用")
        try:
            self.repository.touch_session(int(session["id"]))
        except Exception:  # pragma: no cover
            _LOGGER.exception("Failed to touch session %s", session.get("id"))

        user = self.repository.get_user_by_id(int(session["user_id"]))
        if not user:
            raise AuthServiceError(401, "INVALID_TOKEN", "登录凭证无效")
        return AuthContext(
            session_id=int(session["id"]),
            user_id=int(session["user_id"]),
            user=self._hydrate_user_response(user),
        )

    # ---- helpers ----------------------------------------------------------

    def build_user_response(self, user: dict) -> AuthUserResponse:
        """Public accessor – callers (tests, permission service) use this to
        re-hydrate an :class:`AuthUserResponse` from a raw user row."""
        return self._hydrate_user_response(user)

    def _hydrate_user_response(self, user: dict) -> AuthUserResponse:
        user_id = int(user["id"])
        try:
            roles = self.repository.list_roles_for_user(user_id)
        except Exception:  # pragma: no cover
            roles = []
        try:
            permissions = self.repository.list_permissions_for_user(user_id)
        except Exception:  # pragma: no cover
            permissions = []
        return AuthUserResponse(
            id=user_id,
            username=user["username"],
            display_name=(user.get("display_name") or user["username"]),
            is_super_admin=_as_bool(user.get("is_super_admin")),
            must_change_password=_as_bool(user.get("must_change_password")),
            roles=list(roles),
            permissions=list(permissions),
            is_active=_as_bool(user.get("is_active")),
        )

    def _build_pending_login_response(
        self,
        *,
        user_id: int,
        ip_address: str,
        user_agent: str,
        device_name: str,
    ) -> dict:
        pending_token = _new_token()
        expires_at = _utc_iso(_utc_now() + timedelta(minutes=_pending_login_ttl_min()))
        try:
            self.repository.create_pending_login(
                user_id=user_id,
                pending_token_hash=_token_hash(pending_token),
                ip_address=ip_address,
                user_agent=user_agent,
                device_name=device_name,
                expires_at=expires_at,
            )
        except Exception as exc:  # pragma: no cover
            _LOGGER.exception("Failed to create pending login for %s", user_id)
            raise AuthServiceError(500, "PENDING_LOGIN_FAILED", "创建临时登录凭证失败") from exc

        active_devices = []
        for row in self.repository.list_devices_for_user(user_id):
            if _as_bool(row.get("is_revoked")):
                continue
            active_devices.append(
                {
                    "id": int(row["id"]),
                    "device_name": row.get("device_name") or "",
                    "user_agent": row.get("user_agent") or "",
                    "ip_address": row.get("ip_address") or "",
                    "first_login_at": str(row.get("first_login_at") or row.get("created_at") or ""),
                    "last_active_at": str(row.get("last_active_at") or ""),
                    "is_revoked": False,
                    "revoked_at": None,
                    "active_session_count": int(row.get("active_session_count") or 0),
                    "is_current": False,
                }
            )
        return {
            "requires_device_replacement": True,
            "pending_token": pending_token,
            "expires_at": expires_at,
            "max_devices": _max_active_devices_per_user(),
            "devices": active_devices,
            "message": f"设备数量已达上限（{_max_active_devices_per_user()}），请选择一台要替换的设备",
        }

    def _create_session_and_response(
        self,
        *,
        user: dict,
        user_agent: str,
        ip_address: str,
        device_name: str,
    ) -> dict:
        access_token = _new_token()
        refresh_token = _new_token()
        now = _utc_now()
        access_expires_at = _utc_iso(now + timedelta(minutes=_access_token_ttl_min()))
        refresh_expires_at = _utc_iso(now + timedelta(days=_refresh_token_ttl_days()))
        self.repository.create_session(
            user_id=int(user["id"]),
            access_token_hash=_token_hash(access_token),
            refresh_token_hash=_token_hash(refresh_token),
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
            device_name=device_name,
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_at": access_expires_at,
            "refresh_expires_at": refresh_expires_at,
            "user": self._hydrate_user_response(user),
        }

    # ---- validation -------------------------------------------------------

    @staticmethod
    def _validate_username(username: str) -> None:
        if len(username) < 3 or len(username) > 32:
            raise AuthServiceError(400, "INVALID_USERNAME", "用户名长度必须为 3-32 个字符")
        for ch in username:
            if not (ch.isalnum() or ch in {".", "_", "-"}):
                raise AuthServiceError(
                    400,
                    "INVALID_USERNAME",
                    "用户名只能包含字母、数字、点号、下划线或连字符",
                )

    @staticmethod
    def _validate_password(password: str) -> None:
        if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
            raise AuthServiceError(400, "INVALID_PASSWORD", "密码长度必须为 8-128 个字符")
        if password.strip() != password:
            raise AuthServiceError(400, "INVALID_PASSWORD", "密码开头或结尾不能包含空白字符")
