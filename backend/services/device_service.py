from __future__ import annotations

from app.db.auth_repository import AuthRepository
from backend.models.auth_schemas import AuthDeviceResponse
from backend.services.auth_service import AuthContext, AuthServiceError


MAX_DEVICE_NAME_LENGTH = 64


class DeviceService:
    def __init__(self, repository: AuthRepository | None = None):
        self.repository = repository or AuthRepository()

    def list_devices(self, context: AuthContext) -> list[AuthDeviceResponse]:
        current_device_id = self.repository.get_device_id_for_session(context.session_id)
        devices = self.repository.list_devices_for_user(context.user_id, current_device_id)
        return [_build_device_response(device) for device in devices]

    def rename_device(self, context: AuthContext, device_id: int, device_name: str) -> AuthDeviceResponse:
        normalized_name = _normalize_device_name(device_name)
        current_device_id = self.repository.get_device_id_for_session(context.session_id)
        device = self.repository.rename_device(
            user_id=context.user_id,
            device_id=device_id,
            device_name=normalized_name,
            current_device_id=current_device_id,
        )
        if not device:
            raise AuthServiceError(404, "DEVICE_NOT_FOUND", "设备不存在")
        return _build_device_response(device)

    def revoke_device(self, context: AuthContext, device_id: int) -> AuthDeviceResponse:
        current_device_id = self.repository.get_device_id_for_session(context.session_id)
        device = self.repository.revoke_device(
            user_id=context.user_id,
            device_id=device_id,
            reason="device_revoked",
            current_device_id=current_device_id,
        )
        if not device:
            raise AuthServiceError(404, "DEVICE_NOT_FOUND", "设备不存在")
        return _build_device_response(device)


def _normalize_device_name(device_name: str) -> str:
    clean_value = device_name.strip()
    if not clean_value:
        raise AuthServiceError(400, "INVALID_DEVICE_NAME", "请输入设备名称")
    if len(clean_value) > MAX_DEVICE_NAME_LENGTH:
        raise AuthServiceError(400, "INVALID_DEVICE_NAME", "设备名称长度必须为 1-64 个字符")
    return clean_value


def _build_device_response(device: dict) -> AuthDeviceResponse:
    return AuthDeviceResponse(
        id=device["id"],
        device_name=device["device_name"],
        user_agent=device["user_agent"],
        ip_address=device["ip_address"],
        first_login_at=str(device["first_login_at"]),
        last_active_at=str(device["last_active_at"]),
        is_revoked=bool(device["is_revoked"]),
        revoked_at=device["revoked_at"],
        active_session_count=int(device["active_session_count"]),
        is_current=bool(device["is_current"]),
    )
