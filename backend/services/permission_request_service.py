from __future__ import annotations

from app.db.auth_repository import AuthRepository
from app.db.store import DATABASE_INTEGRITY_ERRORS
from backend.models.auth_schemas import AuthPermissionRequestResponse, AuthPermissionResponse
from backend.services.auth_service import AuthContext, AuthServiceError


VALID_REQUEST_STATUSES = {"pending", "approved", "rejected", "cancelled"}


class PermissionRequestService:
    def __init__(self, repository: AuthRepository | None = None):
        self.repository = repository or AuthRepository()

    def list_permissions(self, context: AuthContext) -> list[AuthPermissionResponse]:
        current_permissions = set(context.user.permissions)
        return [
            AuthPermissionResponse(
                code=permission["code"],
                name=permission["name"],
                module=permission["module"],
                description=permission["description"],
                has_permission=context.user.is_super_admin or permission["code"] in current_permissions,
            )
            for permission in self.repository.list_all_permissions()
        ]

    def create_request(
        self,
        context: AuthContext,
        *,
        permission_code: str,
        reason: str,
    ) -> AuthPermissionRequestResponse:
        normalized_code = permission_code.strip()
        if not normalized_code:
            raise AuthServiceError(400, "INVALID_PERMISSION", "请选择要申请的权限")
        if context.user.is_super_admin or normalized_code in context.user.permissions:
            raise AuthServiceError(409, "PERMISSION_ALREADY_GRANTED", "你已拥有该权限")
        if not self.repository.get_permission_by_code(normalized_code):
            raise AuthServiceError(404, "PERMISSION_NOT_FOUND", "权限不存在")

        try:
            request = self.repository.create_permission_request(
                user_id=context.user_id,
                permission_code=normalized_code,
                reason=reason.strip(),
            )
        except DATABASE_INTEGRITY_ERRORS as exc:
            raise AuthServiceError(409, "PERMISSION_REQUEST_PENDING", "该权限已有待审批申请") from exc
        return _build_permission_request_response(request)

    def list_my_requests(self, context: AuthContext) -> list[AuthPermissionRequestResponse]:
        return [_build_permission_request_response(request) for request in self.repository.list_permission_requests_for_user(context.user_id)]

    def list_review_requests(self, status: str | None = None) -> list[AuthPermissionRequestResponse]:
        normalized_status = (status or "").strip() or None
        if normalized_status and normalized_status not in VALID_REQUEST_STATUSES:
            raise AuthServiceError(400, "INVALID_REQUEST_STATUS", "权限申请状态无效")
        return [_build_permission_request_response(request) for request in self.repository.list_permission_requests(normalized_status)]

    def review_request(
        self,
        context: AuthContext,
        *,
        request_id: int,
        status: str,
        review_comment: str,
    ) -> AuthPermissionRequestResponse:
        normalized_status = status.strip()
        if normalized_status == "approved":
            self._require_review_permission(context, "permission_request:approve")
        elif normalized_status == "rejected":
            self._require_review_permission(context, "permission_request:reject")
        else:
            raise AuthServiceError(400, "INVALID_REVIEW_STATUS", "审批结果只能是通过或拒绝")

        try:
            request = self.repository.review_permission_request(
                request_id=request_id,
                reviewer_id=context.user_id,
                status=normalized_status,
                review_comment=review_comment.strip(),
            )
        except ValueError as exc:
            raise AuthServiceError(409, "PERMISSION_REQUEST_NOT_PENDING", "该权限申请已处理，不能重复审批") from exc
        if not request:
            raise AuthServiceError(404, "PERMISSION_REQUEST_NOT_FOUND", "权限申请不存在")
        return _build_permission_request_response(request)

    @staticmethod
    def _require_review_permission(context: AuthContext, permission_code: str) -> None:
        if context.user.is_super_admin or permission_code in context.user.permissions:
            return
        raise AuthServiceError(403, "PERMISSION_DENIED", f"缺少权限：{permission_code}")


def _build_permission_request_response(request: dict) -> AuthPermissionRequestResponse:
    return AuthPermissionRequestResponse(
        id=request["id"],
        user_id=request["user_id"],
        username=request["username"],
        display_name=request["display_name"],
        permission_code=request["permission_code"],
        permission_name=request["permission_name"],
        permission_module=request["permission_module"],
        reason=request["reason"],
        status=request["status"],
        reviewer_id=request["reviewer_id"],
        reviewer_username=request["reviewer_username"],
        reviewer_display_name=request["reviewer_display_name"],
        review_comment=request["review_comment"],
        created_at=str(request["created_at"]),
        reviewed_at=request["reviewed_at"],
    )
