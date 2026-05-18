from typing import Any

from pydantic import BaseModel, Field


class AuthUserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    is_super_admin: bool = False
    must_change_password: bool = False
    is_active: bool = True


class AuthRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=64)


class AuthRegisterResponse(BaseModel):
    success: bool
    message: str
    user: AuthUserResponse


class AuthLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)
    device_name: str | None = Field(default=None, max_length=64)


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: AuthUserResponse


class AuthPendingLoginResponse(BaseModel):
    requires_device_replacement: bool = True
    pending_token: str
    expires_at: str
    max_devices: int
    devices: list["AuthDeviceResponse"] = Field(default_factory=list)
    message: str


class AuthReplaceDeviceLoginRequest(BaseModel):
    pending_token: str = Field(min_length=16, max_length=256)
    replace_device_id: int = Field(gt=0)


class AuthMeResponse(BaseModel):
    user: AuthUserResponse


class AuthLogoutResponse(BaseModel):
    success: bool
    message: str


class AuthDeviceResponse(BaseModel):
    id: int
    device_name: str
    user_agent: str
    ip_address: str
    first_login_at: str
    last_active_at: str
    is_revoked: bool = False
    revoked_at: str | None = None
    active_session_count: int = 0
    is_current: bool = False


class AuthDeviceListResponse(BaseModel):
    devices: list[AuthDeviceResponse]
    total: int


class AuthDeviceRenameRequest(BaseModel):
    device_name: str = Field(min_length=1, max_length=64)


class AuthDeviceMutationResponse(BaseModel):
    success: bool
    message: str
    device: AuthDeviceResponse


class AuthPermissionResponse(BaseModel):
    code: str
    name: str
    module: str
    description: str
    has_permission: bool = False


class AuthPermissionCatalogResponse(BaseModel):
    permissions: list[AuthPermissionResponse]


class AuthPermissionRequestCreateRequest(BaseModel):
    permission_code: str = Field(min_length=3, max_length=64)
    reason: str = Field(default="", max_length=500)


class AuthPermissionRequestReviewRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    review_comment: str = Field(default="", max_length=500)


class AuthPermissionRequestResponse(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: str
    permission_code: str
    permission_name: str
    permission_module: str
    reason: str
    status: str
    reviewer_id: int | None = None
    reviewer_username: str | None = None
    reviewer_display_name: str | None = None
    review_comment: str = ""
    created_at: str
    reviewed_at: str | None = None


class AuthPermissionRequestListResponse(BaseModel):
    requests: list[AuthPermissionRequestResponse]
    total: int


class AuthPermissionRequestMutationResponse(BaseModel):
    success: bool
    message: str
    request: AuthPermissionRequestResponse


class AuthManagedUserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    is_active: bool = True
    is_super_admin: bool = False
    must_change_password: bool = False
    last_login_at: str | None = None
    created_at: str
    active_session_count: int = 0


class AuthManagedUserListResponse(BaseModel):
    users: list[AuthManagedUserResponse]
    total: int


class AuthManagedUserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=64)
    role_codes: list[str] = Field(default_factory=lambda: ["member"], max_length=12)


class AuthManagedUserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    role_codes: list[str] | None = Field(default=None, max_length=12)
    is_active: bool | None = None


class AuthManagedUserMutationResponse(BaseModel):
    success: bool
    message: str
    user: AuthManagedUserResponse


class AuthManagedUserDeleteResponse(BaseModel):
    success: bool
    message: str


class AuthRoleResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    is_system: bool = False
    permission_codes: list[str] = Field(default_factory=list)
    user_count: int = 0
    created_at: str
    updated_at: str


class AuthRoleListResponse(BaseModel):
    roles: list[AuthRoleResponse]
    total: int


class AuthRoleCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=48)
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=300)
    permission_codes: list[str] = Field(default_factory=list, max_length=128)


class AuthRoleUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=300)
    permission_codes: list[str] = Field(default_factory=list, max_length=128)


class AuthRoleMutationResponse(BaseModel):
    success: bool
    message: str
    role: AuthRoleResponse


class AuthAuditLogResponse(BaseModel):
    id: int
    actor_user_id: int | None = None
    actor_username: str | None = None
    actor_display_name: str | None = None
    target_user_id: int | None = None
    target_username: str | None = None
    target_display_name: str | None = None
    action: str
    module: str
    description: str
    ip_address: str
    user_agent: str
    result: str
    created_at: str


class AuthAuditLogListResponse(BaseModel):
    logs: list[AuthAuditLogResponse]
    total: int


class AuditTrackRequest(BaseModel):
    module: str = Field(min_length=1, max_length=32)
    action: str = Field(min_length=1, max_length=64)
    description: str = ""
    metadata: dict[str, Any] | None = None


class AuditTrackResponse(BaseModel):
    success: bool
    throttled: bool = False
