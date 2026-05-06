from __future__ import annotations

import logging

from app.db.auth_repository import AuthRepository
from backend.models.auth_schemas import AuthAuditLogResponse


VALID_AUDIT_RESULTS = {"success", "failure", "pending"}
MAX_AUDIT_LIMIT = 200


class AuditLogService:
    def __init__(self, repository: AuthRepository | None = None):
        self.repository = repository or AuthRepository()

    def record(
        self,
        *,
        action: str,
        module: str = "auth",
        description: str = "",
        actor_user_id: int | None = None,
        target_user_id: int | None = None,
        ip_address: str = "",
        user_agent: str = "",
        result: str = "success",
    ) -> None:
        clean_action = action.strip()
        clean_module = module.strip() or "auth"
        clean_result = result.strip() or "success"
        if not clean_action:
            return
        if clean_result not in VALID_AUDIT_RESULTS:
            clean_result = "success"

        try:
            self.repository.create_audit_log(
                actor_user_id=actor_user_id,
                target_user_id=target_user_id,
                action=clean_action,
                module=clean_module,
                description=description.strip(),
                ip_address=ip_address.strip(),
                user_agent=user_agent.strip(),
                result=clean_result,
            )
        except Exception:
            logging.exception("Failed to write auth audit log: %s", clean_action)

    def list_logs(
        self,
        *,
        limit: int = 100,
        module: str | None = None,
        action: str | None = None,
        result: str | None = None,
        actor_user_id: int | None = None,
        target_user_id: int | None = None,
    ) -> list[AuthAuditLogResponse]:
        clean_result = (result or "").strip() or None
        if clean_result and clean_result not in VALID_AUDIT_RESULTS:
            clean_result = None

        rows = self.repository.list_audit_logs(
            limit=max(1, min(int(limit or 100), MAX_AUDIT_LIMIT)),
            module=(module or "").strip() or None,
            action=(action or "").strip() or None,
            result=clean_result,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
        )
        return [_build_audit_log_response(row) for row in rows]


def _build_audit_log_response(row: dict) -> AuthAuditLogResponse:
    return AuthAuditLogResponse(
        id=row["id"],
        actor_user_id=row["actor_user_id"],
        actor_username=row["actor_username"],
        actor_display_name=row["actor_display_name"],
        target_user_id=row["target_user_id"],
        target_username=row["target_username"],
        target_display_name=row["target_display_name"],
        action=row["action"],
        module=row["module"],
        description=row["description"],
        ip_address=row["ip_address"],
        user_agent=row["user_agent"],
        result=row["result"],
        created_at=str(row["created_at"]),
    )
