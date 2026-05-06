from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.services.auth_service import AuthContext, AuthService, AuthServiceError


security = HTTPBearer(auto_error=False)
auth_service = AuthService()


def auth_http_exception(error: AuthServiceError, headers: dict[str, str] | None = None) -> HTTPException:
    return HTTPException(
        status_code=error.status_code,
        detail={"code": error.code, "message": error.message},
        headers=headers,
    )


def get_current_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> AuthContext:
    if credentials is None:
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "请先登录"})

    try:
        context = auth_service.authenticate_access_token(credentials.credentials)
    except AuthServiceError as exc:
        raise auth_http_exception(exc) from exc

    # Expose the authenticated context to downstream middleware (audit logger).
    request.state.auth_context = context
    return context


def require_permission(permission_code: str) -> Callable[[AuthContext], AuthContext]:
    def dependency(context: AuthContext = Depends(get_current_auth_context)) -> AuthContext:
        if context.user.is_super_admin or permission_code in context.user.permissions:
            return context
        raise HTTPException(
            status_code=403,
            detail={"code": "PERMISSION_DENIED", "message": f"缺少权限：{permission_code}"},
        )

    return dependency
