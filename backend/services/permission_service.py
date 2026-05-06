from __future__ import annotations

from dataclasses import dataclass

from app.db.auth_repository import AuthRepository


@dataclass(frozen=True)
class EffectivePermissions:
    user_id: int
    roles: list[str]
    permissions: list[str]
    is_super_admin: bool

    def has(self, permission_code: str) -> bool:
        return self.is_super_admin or permission_code in self.permissions


class PermissionService:
    def __init__(self, repository: AuthRepository | None = None):
        self.repository = repository or AuthRepository()

    def get_effective_permissions(self, user: dict) -> EffectivePermissions:
        user_id = user["id"]
        is_super_admin = _as_bool(user["is_super_admin"])
        return EffectivePermissions(
            user_id=user_id,
            roles=self.repository.list_roles_for_user(user_id),
            permissions=self.repository.list_permissions_for_user(user_id),
            is_super_admin=is_super_admin,
        )

    def has_permission(self, user: dict, permission_code: str) -> bool:
        return self.get_effective_permissions(user).has(permission_code)


def _as_bool(value: object) -> bool:
    return bool(int(value)) if isinstance(value, int | str) else bool(value)
