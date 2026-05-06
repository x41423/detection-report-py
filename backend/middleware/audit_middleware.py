"""Automatic audit logging for state-changing API calls.

Records one entry in ``auth_audit_logs`` per mutating HTTP request (POST /
PUT / PATCH / DELETE) under ``/api/*``. The actor is resolved from
``request.state.auth_context`` which must be set by the auth dependency when
a valid access token is presented.

A curated skip list avoids double-logging endpoints that already call
:class:`~backend.services.audit_log_service.AuditLogService.record` manually
(most ``/api/auth/*`` endpoints), the audit track endpoint itself (to avoid
feedback loops), and health probes.
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.middleware._request_meta import client_ip, user_agent
from backend.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


# Endpoints that handle their own auditing (see backend/api/routes/auth.py).
# The audit track endpoint is excluded to prevent recursive log-on-log.
_SKIP_EXACT_PATHS: frozenset[str] = frozenset(
    {
        "/api/audit/track",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/register",
        "/api/auth/refresh",
        "/api/auth/replace-device-login",
        "/api/health",
    }
)

# Prefixes whose endpoints already emit structured audit entries.
_SKIP_PREFIXES: tuple[str, ...] = (
    "/api/auth/devices",
    "/api/auth/users",
    "/api/auth/roles",
    "/api/auth/permission-requests",
    "/api/auth/permissions",
)

_AUDITED_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Map the first path segment after ``/api/`` to a logical ``module`` label.
_MODULE_ALIASES: dict[str, str] = {
    "daily-intake": "daily_intake",
    "weekly-price": "weekly_price",
}


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, service: AuditLogService | None = None) -> None:
        super().__init__(app)
        self._service = service or AuditLogService()

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        should_audit = self._should_audit(request)
        response: Response = await call_next(request)
        if should_audit:
            try:
                self._record(request, response)
            except Exception:  # pragma: no cover - logging must never break responses
                logger.exception("audit middleware record() failed")
        return response

    # ------------------------------------------------------------------
    # internals

    def _should_audit(self, request: Request) -> bool:
        if request.method.upper() not in _AUDITED_METHODS:
            return False
        path = request.url.path
        if not path.startswith("/api/"):
            return False
        if path in _SKIP_EXACT_PATHS:
            return False
        if any(path.startswith(prefix) for prefix in _SKIP_PREFIXES):
            return False
        return True

    def _record(self, request: Request, response: Response) -> None:
        method = request.method.upper()
        path = request.url.path
        route_template = self._route_template(request) or path
        module = self._module_for_path(path)
        status_code = int(getattr(response, "status_code", 0) or 0)
        result = "success" if 200 <= status_code < 400 else "failure"
        actor_user_id = self._actor_user_id(request)

        description = f"status={status_code} path={path}"

        self._service.record(
            action=f"{method} {route_template}",
            module=module,
            description=description,
            actor_user_id=actor_user_id,
            ip_address=client_ip(request),
            user_agent=user_agent(request),
            result=result,
        )

    @staticmethod
    def _route_template(request: Request) -> str | None:
        route: Any = request.scope.get("route")
        template = getattr(route, "path", None)
        if isinstance(template, str) and template:
            return template
        return None

    @staticmethod
    def _module_for_path(path: str) -> str:
        # Expect ``/api/<module>/...``; fall back to ``api`` when the path is
        # short enough that no module segment exists.
        trimmed = path[len("/api/") :] if path.startswith("/api/") else path.lstrip("/")
        head = trimmed.split("/", 1)[0] or "api"
        return _MODULE_ALIASES.get(head, head.replace("-", "_"))

    @staticmethod
    def _actor_user_id(request: Request) -> int | None:
        context = getattr(request.state, "auth_context", None)
        user = getattr(context, "user", None)
        user_id = getattr(user, "id", None)
        try:
            return int(user_id) if user_id is not None else None
        except (TypeError, ValueError):
            return None
