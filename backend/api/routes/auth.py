from fastapi import APIRouter, Depends, Query, Request, Response

from backend.auth.cookies import clear_refresh_cookie, clear_refresh_cookie_header, refresh_cookie_name, set_refresh_cookie
from backend.auth.dependencies import AuthContext, auth_http_exception, get_current_auth_context, require_permission
from backend.models.auth_schemas import (
    AuthDeviceListResponse,
    AuthDeviceMutationResponse,
    AuthDeviceRenameRequest,
    AuthAuditLogListResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthLogoutResponse,
    AuthManagedUserCreateRequest,
    AuthManagedUserDeleteResponse,
    AuthManagedUserListResponse,
    AuthManagedUserMutationResponse,
    AuthManagedUserUpdateRequest,
    AuthMeResponse,
    AuthPendingLoginResponse,
    AuthPermissionCatalogResponse,
    AuthPermissionRequestCreateRequest,
    AuthPermissionRequestListResponse,
    AuthPermissionRequestMutationResponse,
    AuthPermissionRequestReviewRequest,
    AuthRegisterRequest,
    AuthRegisterResponse,
    AuthReplaceDeviceLoginRequest,
    AuthRoleCreateRequest,
    AuthRoleListResponse,
    AuthRoleMutationResponse,
    AuthRoleResponse,
    AuthRoleUpdateRequest,
)
from backend.services.audit_log_service import AuditLogService
from backend.services.auth_service import AuthService, AuthServiceError
from backend.services.device_service import DeviceService
from backend.services.permission_request_service import PermissionRequestService
from backend.services.user_role_management_service import UserRoleManagementService


router = APIRouter()
auth_service = AuthService()
device_service = DeviceService()
permission_request_service = PermissionRequestService()
user_role_management_service = UserRoleManagementService()
audit_log_service = AuditLogService()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else ""


def _audit_from_request(
    request: Request,
    *,
    action: str,
    module: str = "auth",
    description: str = "",
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    result: str = "success",
) -> None:
    audit_log_service.record(
        action=action,
        module=module,
        description=description,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        result=result,
    )


def _user_id_for_username(username: str) -> int | None:
    try:
        user = auth_service.repository.get_user_by_username((username or "").strip().lower())
    except Exception:
        return None
    return int(user["id"]) if user else None


def _token_response(auth_result: dict, response: Response) -> AuthLoginResponse:
    refresh_token = auth_result.pop("refresh_token")
    auth_result.pop("refresh_expires_at", None)
    set_refresh_cookie(response, refresh_token)
    return AuthLoginResponse(**auth_result)


# ---------------------------------------------------------------------------
# authentication endpoints


@router.post("/register", response_model=AuthRegisterResponse)
def register(req: AuthRegisterRequest, request: Request):
    try:
        user = auth_service.register(username=req.username, password=req.password, display_name=req.display_name)
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="register",
            module="auth",
            description=f"注册用户 {req.username} 失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="register",
        module="auth",
        target_user_id=user.id,
        description=f"已注册用户 {user.username}",
    )
    return AuthRegisterResponse(success=True, message="注册成功", user=user)


@router.post("/login", response_model=AuthLoginResponse | AuthPendingLoginResponse)
def login(req: AuthLoginRequest, request: Request, response: Response):
    try:
        auth_result = auth_service.login(
            username=req.username,
            password=req.password,
            user_agent=request.headers.get("user-agent", ""),
            ip_address=_client_ip(request),
            device_name=req.device_name,
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="login",
            module="auth",
            target_user_id=_user_id_for_username(req.username),
            description=f"用户 {req.username} 登录失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    if auth_result.get("requires_device_replacement"):
        _audit_from_request(
            request,
            action="login_device_limit",
            module="auth",
            target_user_id=_user_id_for_username(req.username),
            description=f"用户 {req.username} 登录需要替换设备",
            result="pending",
        )
        response.status_code = 202
        return AuthPendingLoginResponse(**auth_result)
    user = auth_result["user"]
    _audit_from_request(
        request,
        action="login",
        module="auth",
        actor_user_id=user.id,
        target_user_id=user.id,
        description=f"用户 {user.username} 已登录",
    )
    return _token_response(auth_result, response)


@router.post("/device-replacement", response_model=AuthLoginResponse)
def replace_device_login(req: AuthReplaceDeviceLoginRequest, request: Request, response: Response):
    try:
        auth_result = auth_service.replace_device_login(
            pending_token=req.pending_token,
            replace_device_id=req.replace_device_id,
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="device_replace_login",
            module="device",
            description=f"设备替换登录失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    user = auth_result["user"]
    _audit_from_request(
        request,
        action="device_replace_login",
        module="device",
        actor_user_id=user.id,
        target_user_id=user.id,
        description=f"用户 {user.username} 登录时替换了设备 {req.replace_device_id}",
    )
    return _token_response(auth_result, response)


@router.post("/refresh", response_model=AuthLoginResponse)
def refresh(request: Request, response: Response):
    try:
        auth_result = auth_service.refresh(
            refresh_token=request.cookies.get(refresh_cookie_name(), ""),
            user_agent=request.headers.get("user-agent", ""),
            ip_address=_client_ip(request),
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="refresh",
            module="auth",
            description=f"会话刷新失败：{exc.code}",
            result="failure",
        )
        clear_refresh_cookie(response)
        raise auth_http_exception(exc, headers={"set-cookie": clear_refresh_cookie_header()}) from exc
    return _token_response(auth_result, response)


@router.get("/me", response_model=AuthMeResponse)
def me(context: AuthContext = Depends(get_current_auth_context)):
    return AuthMeResponse(user=context.user)


@router.post("/logout", response_model=AuthLogoutResponse)
def logout(request: Request, response: Response, context: AuthContext = Depends(get_current_auth_context)):
    auth_service.logout(session_id=context.session_id)
    _audit_from_request(
        request,
        action="logout",
        module="auth",
        actor_user_id=context.user_id,
        target_user_id=context.user_id,
        description=f"用户 {context.user.username} 已退出登录",
    )
    clear_refresh_cookie(response)
    return AuthLogoutResponse(success=True, message="已退出登录")


# ---------------------------------------------------------------------------
# device endpoints


@router.get("/devices", response_model=AuthDeviceListResponse)
def list_devices(context: AuthContext = Depends(require_permission("device:view"))):
    devices = device_service.list_devices(context)
    return AuthDeviceListResponse(devices=devices, total=len(devices))


@router.put("/devices/{device_id}", response_model=AuthDeviceMutationResponse)
def rename_device(
    device_id: int,
    req: AuthDeviceRenameRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("device:rename")),
):
    try:
        device = device_service.rename_device(context, device_id, req.device_name)
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="device_rename",
            module="device",
            actor_user_id=context.user_id,
            target_user_id=context.user_id,
            description=f"设备 {device_id} 重命名失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="device_rename",
        module="device",
        actor_user_id=context.user_id,
        target_user_id=context.user_id,
        description=f"已重命名设备 {device.id}",
    )
    return AuthDeviceMutationResponse(success=True, message="设备已重命名", device=device)


@router.delete("/devices/{device_id}", response_model=AuthDeviceMutationResponse)
def revoke_device(
    device_id: int,
    request: Request,
    response: Response,
    context: AuthContext = Depends(require_permission("device:revoke")),
):
    try:
        device = device_service.revoke_device(context, device_id)
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="device_revoke",
            module="device",
            actor_user_id=context.user_id,
            target_user_id=context.user_id,
            description=f"设备 {device_id} 下线失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    if device.is_current:
        clear_refresh_cookie(response)
    _audit_from_request(
        request,
        action="device_revoke",
        module="device",
        actor_user_id=context.user_id,
        target_user_id=context.user_id,
        description=f"已下线设备 {device.id}",
    )
    return AuthDeviceMutationResponse(success=True, message="设备已下线", device=device)


# ---------------------------------------------------------------------------
# permissions & permission requests


@router.get("/permissions", response_model=AuthPermissionCatalogResponse)
def list_permissions_catalog(context: AuthContext = Depends(get_current_auth_context)):
    permissions = permission_request_service.list_permissions(context)
    return AuthPermissionCatalogResponse(permissions=permissions)


@router.get("/permission-requests/mine", response_model=AuthPermissionRequestListResponse)
def list_my_permission_requests(context: AuthContext = Depends(get_current_auth_context)):
    requests = permission_request_service.list_my_requests(context)
    return AuthPermissionRequestListResponse(requests=requests, total=len(requests))


@router.post("/permission-requests", response_model=AuthPermissionRequestMutationResponse)
def create_permission_request(
    req: AuthPermissionRequestCreateRequest,
    request: Request,
    context: AuthContext = Depends(get_current_auth_context),
):
    try:
        created = permission_request_service.create_request(
            context,
            permission_code=req.permission_code,
            reason=req.reason,
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="permission_request_create",
            module="permission",
            actor_user_id=context.user_id,
            target_user_id=context.user_id,
            description=f"提交权限申请失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="permission_request_create",
        module="permission",
        actor_user_id=context.user_id,
        target_user_id=context.user_id,
        description=f"已提交权限申请：{req.permission_code}",
    )
    return AuthPermissionRequestMutationResponse(success=True, message="已提交权限申请", request=created)


@router.get("/permission-requests", response_model=AuthPermissionRequestListResponse)
def list_all_permission_requests(
    status: str | None = Query(default=None),
    context: AuthContext = Depends(require_permission("permission_request:view")),
):
    try:
        requests = permission_request_service.list_review_requests(status)
    except AuthServiceError as exc:
        raise auth_http_exception(exc) from exc
    return AuthPermissionRequestListResponse(requests=requests, total=len(requests))


@router.post(
    "/permission-requests/{request_id}/review",
    response_model=AuthPermissionRequestMutationResponse,
)
def review_permission_request(
    request_id: int,
    req: AuthPermissionRequestReviewRequest,
    request: Request,
    context: AuthContext = Depends(get_current_auth_context),
):
    try:
        reviewed = permission_request_service.review_request(
            context,
            request_id=request_id,
            status=req.status,
            review_comment=req.review_comment,
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="permission_request_review",
            module="permission",
            actor_user_id=context.user_id,
            description=f"审批权限申请 {request_id} 失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="permission_request_review",
        module="permission",
        actor_user_id=context.user_id,
        target_user_id=reviewed.user_id,
        description=f"已{req.status}权限申请 {request_id}",
    )
    return AuthPermissionRequestMutationResponse(success=True, message="审批已保存", request=reviewed)


# ---------------------------------------------------------------------------
# managed users


@router.get("/users", response_model=AuthManagedUserListResponse)
def list_managed_users(context: AuthContext = Depends(require_permission("user:view"))):
    users = user_role_management_service.list_users()
    return AuthManagedUserListResponse(users=users, total=len(users))


@router.post("/users", response_model=AuthManagedUserMutationResponse)
def create_managed_user(
    req: AuthManagedUserCreateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("user:create")),
):
    try:
        created = user_role_management_service.create_user(
            username=req.username,
            password=req.password,
            display_name=req.display_name,
            role_codes=req.role_codes,
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="user_create",
            module="user",
            actor_user_id=context.user_id,
            description=f"创建用户 {req.username} 失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="user_create",
        module="user",
        actor_user_id=context.user_id,
        target_user_id=created.id,
        description=f"已创建用户 {created.username}",
    )
    return AuthManagedUserMutationResponse(success=True, message="用户已创建", user=created)


@router.patch("/users/{user_id}", response_model=AuthManagedUserMutationResponse)
def update_managed_user(
    user_id: int,
    req: AuthManagedUserUpdateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("user:update")),
):
    try:
        updated = user_role_management_service.update_user(
            context,
            user_id=user_id,
            display_name=req.display_name,
            role_codes=req.role_codes,
            is_active=req.is_active,
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="user_update",
            module="user",
            actor_user_id=context.user_id,
            target_user_id=user_id,
            description=f"更新用户 {user_id} 失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="user_update",
        module="user",
        actor_user_id=context.user_id,
        target_user_id=user_id,
        description=f"已更新用户 {updated.username}",
    )
    return AuthManagedUserMutationResponse(success=True, message="用户已更新", user=updated)


@router.delete("/users/{user_id}", response_model=AuthManagedUserDeleteResponse)
def delete_managed_user(
    user_id: int,
    request: Request,
    context: AuthContext = Depends(require_permission("user:delete")),
):
    try:
        deleted = user_role_management_service.delete_user(context, user_id)
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="user_delete",
            module="user",
            actor_user_id=context.user_id,
            description=f"删除用户 {user_id} 失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="user_delete",
        module="user",
        actor_user_id=context.user_id,
        description=f"已删除用户 {deleted['username']} (ID: {deleted['id']})",
    )
    return AuthManagedUserDeleteResponse(success=True, message="用户已删除")


# ---------------------------------------------------------------------------
# roles


@router.get("/roles", response_model=AuthRoleListResponse)
def list_roles(context: AuthContext = Depends(require_permission("role:view"))):
    roles = user_role_management_service.list_roles()
    return AuthRoleListResponse(roles=roles, total=len(roles))


@router.post("/roles", response_model=AuthRoleMutationResponse)
def create_role(
    req: AuthRoleCreateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("role:create")),
):
    try:
        created = user_role_management_service.create_role(
            code=req.code,
            name=req.name,
            description=req.description,
            permission_codes=req.permission_codes,
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="role_create",
            module="role",
            actor_user_id=context.user_id,
            description=f"创建角色 {req.code} 失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="role_create",
        module="role",
        actor_user_id=context.user_id,
        description=f"已创建角色 {created.code}",
    )
    return AuthRoleMutationResponse(success=True, message="角色已创建", role=created)


@router.put("/roles/{role_id}", response_model=AuthRoleMutationResponse)
def update_role(
    role_id: int,
    req: AuthRoleUpdateRequest,
    request: Request,
    context: AuthContext = Depends(require_permission("role:update")),
):
    try:
        updated = user_role_management_service.update_role(
            role_id=role_id,
            name=req.name,
            description=req.description,
            permission_codes=req.permission_codes,
        )
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="role_update",
            module="role",
            actor_user_id=context.user_id,
            description=f"更新角色 {role_id} 失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="role_update",
        module="role",
        actor_user_id=context.user_id,
        description=f"已更新角色 {updated.code}",
    )
    return AuthRoleMutationResponse(success=True, message="角色已更新", role=updated)


@router.delete("/roles/{role_id}", response_model=AuthRoleMutationResponse)
def delete_role(
    role_id: int,
    request: Request,
    context: AuthContext = Depends(require_permission("role:delete")),
):
    try:
        roles = user_role_management_service.list_roles()
        role = next((r for r in roles if r.id == role_id), None)
        user_role_management_service.delete_role(role_id)
    except AuthServiceError as exc:
        _audit_from_request(
            request,
            action="role_delete",
            module="role",
            actor_user_id=context.user_id,
            description=f"删除角色 {role_id} 失败：{exc.code}",
            result="failure",
        )
        raise auth_http_exception(exc) from exc
    _audit_from_request(
        request,
        action="role_delete",
        module="role",
        actor_user_id=context.user_id,
        description=f"已删除角色 {role_id}",
    )
    return AuthRoleMutationResponse(
        success=True,
        message="角色已删除",
        role=role if role is not None else AuthRoleResponse.model_construct(
            id=role_id, code="", name="", description="", is_system=False,
            permission_codes=[], user_count=0, created_at="", updated_at="",
        ),
    )


# ---------------------------------------------------------------------------
# audit logs


@router.get("/audit-logs", response_model=AuthAuditLogListResponse)
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=200),
    module: str | None = Query(default=None),
    action: str | None = Query(default=None),
    result: str | None = Query(default=None),
    actor_user_id: int | None = Query(default=None),
    target_user_id: int | None = Query(default=None),
    context: AuthContext = Depends(require_permission("audit_log:view")),
):
    logs = audit_log_service.list_logs(
        limit=limit,
        module=module,
        action=action,
        result=result,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
    )
    return AuthAuditLogListResponse(logs=logs, total=len(logs))
