from __future__ import annotations

import re
from typing import Any

from app.db.auth_repository import AuthRepository
from app.db.store import DATABASE_INTEGRITY_ERRORS
from backend.auth.passwords import generate_password_salt, hash_password
from backend.models.auth_schemas import AuthManagedUserResponse, AuthRoleResponse
from backend.services.auth_service import AuthContext, AuthServiceError


USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")
ROLE_CODE_PATTERN = re.compile(r"^[a-z0-9_.-]+$")
DEFAULT_ROLE_CODES = ["member"]
RESERVED_SUPER_ADMIN_ROLE = "super_admin"


class UserRoleManagementService:
    def __init__(self, repository: AuthRepository | None = None):
        self.repository = repository or AuthRepository()

    def list_users(self) -> list[AuthManagedUserResponse]:
        return [_build_managed_user_response(self.repository, user) for user in self.repository.list_users()]

    def create_user(
        self,
        *,
        username: str,
        password: str,
        display_name: str | None,
        role_codes: list[str],
    ) -> AuthManagedUserResponse:
        normalized_username = _normalize_username(username)
        clean_display_name = _normalize_display_name(display_name, normalized_username)
        clean_roles = _normalize_role_codes(role_codes or DEFAULT_ROLE_CODES)
        _validate_username(normalized_username)
        _validate_password(password)
        _reject_reserved_role_assignment(clean_roles)

        if self.repository.get_user_by_username(normalized_username):
            raise AuthServiceError(409, "USERNAME_EXISTS", "用户名已存在")

        salt = generate_password_salt()
        try:
            user = self.repository.create_managed_user(
                username=normalized_username,
                display_name=clean_display_name,
                password_hash=hash_password(password, salt),
                password_salt=salt,
                role_codes=clean_roles,
            )
        except DATABASE_INTEGRITY_ERRORS as exc:
            raise AuthServiceError(409, "USERNAME_EXISTS", "用户名已存在") from exc
        except ValueError as exc:
            raise AuthServiceError(400, "INVALID_ROLE", "包含无效角色") from exc
        return _build_managed_user_response(self.repository, _user_row_for_response(user))

    def update_user(
        self,
        context: AuthContext,
        *,
        user_id: int,
        display_name: str | None,
        role_codes: list[str] | None,
        is_active: bool | None,
    ) -> AuthManagedUserResponse:
        if display_name is not None or role_codes is not None:
            _require_permission(context, "user:update")
        if is_active is not None:
            _require_permission(context, "user:disable")

        target = self.repository.get_user_by_id(user_id)
        if not target:
            raise AuthServiceError(404, "USER_NOT_FOUND", "用户不存在")
        # 管理员不能编辑超级管理员
        if _as_bool(target["is_super_admin"]) and not context.user.is_super_admin:
            raise AuthServiceError(403, "SUPER_ADMIN_PROTECTED", "只有超级管理员可以修改超级管理员账号")
        if role_codes is not None and _as_bool(target["is_super_admin"]):
            raise AuthServiceError(403, "SUPER_ADMIN_ROLE_LOCKED", "超级管理员角色不能被修改")
        if role_codes is not None:
            role_codes = _normalize_role_codes(role_codes)
            _reject_reserved_role_assignment(role_codes)
        if is_active is False and context.user_id == user_id:
            raise AuthServiceError(400, "CANNOT_DISABLE_SELF", "不能停用自己的账号")

        try:
            user = self.repository.update_managed_user(
                user_id=user_id,
                display_name=display_name.strip() if display_name is not None else None,
                role_codes=role_codes,
                is_active=is_active,
            )
        except ValueError as exc:
            raise AuthServiceError(400, "INVALID_ROLE", "包含无效角色") from exc
        if not user:
            raise AuthServiceError(404, "USER_NOT_FOUND", "用户不存在")
        return _build_managed_user_response(self.repository, _user_row_for_response(user))

    def delete_user(self, context: AuthContext, user_id: int) -> dict:
        # 管理员不能删除自己
        if context.user_id == user_id:
            raise AuthServiceError(400, "CANNOT_DELETE_SELF", "不能删除自己的账号")

        target = self.repository.get_user_by_id(user_id)
        if not target:
            raise AuthServiceError(404, "USER_NOT_FOUND", "用户不存在")

        # 超级管理员账号不能被任何人删除
        if _as_bool(target["is_super_admin"]):
            raise AuthServiceError(403, "SUPER_ADMIN_PROTECTED", "超级管理员账号不能删除")

        # 管理员删除用户时，不能删除其他管理员
        if not context.user.is_super_admin:
            target_roles = self.repository.list_roles_for_user(user_id)
            if any(r["code"] == "admin" for r in target_roles):
                raise AuthServiceError(403, "ADMIN_PROTECTED", "管理员账号不能删除")

        if not self.repository.delete_managed_user(user_id):
            raise AuthServiceError(404, "USER_NOT_FOUND", "用户不存在")
        return {
            "id": int(target["id"]),
            "username": target["username"],
            "display_name": target["display_name"],
        }

    def list_roles(self) -> list[AuthRoleResponse]:
        return [_build_role_response(role) for role in self.repository.list_roles()]

    def create_role(
        self,
        *,
        code: str,
        name: str,
        description: str,
        permission_codes: list[str],
    ) -> AuthRoleResponse:
        normalized_code = code.strip().lower()
        _validate_role_code(normalized_code)
        if normalized_code == RESERVED_SUPER_ADMIN_ROLE:
            raise AuthServiceError(400, "RESERVED_ROLE", "超级管理员角色为系统保留角色")
        if self.repository.get_role_by_code(normalized_code):
            raise AuthServiceError(409, "ROLE_EXISTS", "角色已存在")

        try:
            role = self.repository.create_role(
                code=normalized_code,
                name=name.strip(),
                description=description.strip(),
                permission_codes=_normalize_permission_codes(permission_codes),
            )
        except ValueError as exc:
            raise AuthServiceError(400, "INVALID_PERMISSION", "包含无效权限") from exc
        except DATABASE_INTEGRITY_ERRORS as exc:
            raise AuthServiceError(409, "ROLE_EXISTS", "角色已存在") from exc
        return _build_role_response(role)

    def update_role(
        self,
        *,
        role_id: int,
        name: str,
        description: str,
        permission_codes: list[str],
    ) -> AuthRoleResponse:
        role = self.repository.get_role_by_id(role_id)
        if not role:
            raise AuthServiceError(404, "ROLE_NOT_FOUND", "角色不存在")
        if role["code"] == RESERVED_SUPER_ADMIN_ROLE:
            raise AuthServiceError(403, "SUPER_ADMIN_ROLE_LOCKED", "超级管理员角色不能被编辑")

        try:
            updated_role = self.repository.update_role(
                role_id=role_id,
                name=name.strip(),
                description=description.strip(),
                permission_codes=_normalize_permission_codes(permission_codes),
            )
        except ValueError as exc:
            raise AuthServiceError(400, "INVALID_PERMISSION", "包含无效权限") from exc
        if not updated_role:
            raise AuthServiceError(404, "ROLE_NOT_FOUND", "角色不存在")
        return _build_role_response(updated_role)

    def delete_role(self, role_id: int) -> None:
        role = self.repository.get_role_by_id(role_id)
        if not role:
            raise AuthServiceError(404, "ROLE_NOT_FOUND", "角色不存在")
        if role["is_system"]:
            raise AuthServiceError(409, "SYSTEM_ROLE_PROTECTED", "系统角色不能删除")
        if role["user_count"] > 0:
            raise AuthServiceError(409, "ROLE_IN_USE", "仍有用户正在使用该角色")
        if not self.repository.delete_role(role_id):
            raise AuthServiceError(404, "ROLE_NOT_FOUND", "角色不存在")


def _build_managed_user_response(repository: AuthRepository, user: dict) -> AuthManagedUserResponse:
    user_id = user["id"]
    return AuthManagedUserResponse(
        id=user_id,
        username=user["username"],
        display_name=user["display_name"],
        roles=repository.list_roles_for_user(user_id),
        permissions=repository.list_permissions_for_user(user_id),
        is_active=_as_bool(user["is_active"]),
        is_super_admin=_as_bool(user["is_super_admin"]),
        must_change_password=_as_bool(user["must_change_password"]),
        last_login_at=user["last_login_at"],
        created_at=str(user["created_at"]),
        active_session_count=int(user.get("active_session_count", 0) or 0),
    )


def _build_role_response(role: dict) -> AuthRoleResponse:
    return AuthRoleResponse(
        id=role["id"],
        code=role["code"],
        name=role["name"],
        description=role["description"],
        is_system=_as_bool(role["is_system"]),
        permission_codes=role["permission_codes"],
        user_count=int(role["user_count"]),
        created_at=str(role["created_at"]),
        updated_at=str(role["updated_at"]),
    )


def _normalize_username(username: str) -> str:
    return username.strip().lower()


def _normalize_display_name(display_name: str | None, fallback: str) -> str:
    clean_value = (display_name or "").strip()
    return clean_value or fallback


def _normalize_role_codes(role_codes: list[str]) -> list[str]:
    return list(dict.fromkeys(role_code.strip().lower() for role_code in role_codes if role_code.strip()))


def _normalize_permission_codes(permission_codes: list[str]) -> list[str]:
    return list(dict.fromkeys(permission_code.strip() for permission_code in permission_codes if permission_code.strip()))


def _validate_username(username: str) -> None:
    if len(username) < 3 or len(username) > 32:
        raise AuthServiceError(400, "INVALID_USERNAME", "用户名长度必须为 3-32 个字符")
    if not USERNAME_PATTERN.fullmatch(username):
        raise AuthServiceError(400, "INVALID_USERNAME", "用户名只能包含字母、数字、点号、下划线或连字符")


def _validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 128:
        raise AuthServiceError(400, "INVALID_PASSWORD", "密码长度必须为 8-128 个字符")
    if password.strip() != password:
        raise AuthServiceError(400, "INVALID_PASSWORD", "密码开头或结尾不能包含空白字符")


def _validate_role_code(role_code: str) -> None:
    if len(role_code) < 2 or len(role_code) > 48:
        raise AuthServiceError(400, "INVALID_ROLE_CODE", "角色编码长度必须为 2-48 个字符")
    if not ROLE_CODE_PATTERN.fullmatch(role_code):
        raise AuthServiceError(400, "INVALID_ROLE_CODE", "角色编码只能包含小写字母、数字、点号、下划线或连字符")


def _reject_reserved_role_assignment(role_codes: list[str]) -> None:
    if RESERVED_SUPER_ADMIN_ROLE in role_codes:
        raise AuthServiceError(400, "RESERVED_ROLE", "不能在用户管理中分配超级管理员角色")


def _require_permission(context: AuthContext, permission_code: str) -> None:
    if context.user.is_super_admin or permission_code in context.user.permissions:
        return
    raise AuthServiceError(403, "PERMISSION_DENIED", f"缺少权限：{permission_code}")


def _as_bool(value: Any) -> bool:
    return bool(int(value)) if isinstance(value, int | str) else bool(value)


def _user_row_for_response(user: dict) -> dict:
    if "active_session_count" in user:
        return user
    return {
        **user,
        "active_session_count": 0,
    }
