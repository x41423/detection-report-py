"""Frontend-driven audit events (page views, feature clicks, ...)."""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from threading import Lock

from fastapi import APIRouter, Depends, Request

from backend.auth.dependencies import get_current_auth_context, require_permission
from backend.middleware._request_meta import client_ip, user_agent
from backend.models.auth_schemas import AuditTrackRequest, AuditTrackResponse
from backend.services.audit_log_service import AuditLogService
from backend.services.auth_service import AuthContext

router = APIRouter()
audit_log_service = AuditLogService()


# ---------------------------------------------------------------------------
# in-memory debounce to suppress rapid duplicates from chatty clients

_DEBOUNCE_WINDOW_SECONDS = 1.0
_DEBOUNCE_MAX_ENTRIES = 512
_debounce_lock = Lock()
_debounce_cache: "OrderedDict[tuple[int | None, str, str], float]" = OrderedDict()


def _is_duplicate(actor_id: int | None, module: str, action: str) -> bool:
    now = time.monotonic()
    key = (actor_id, module, action)
    with _debounce_lock:
        previous = _debounce_cache.get(key)
        if previous is not None and (now - previous) < _DEBOUNCE_WINDOW_SECONDS:
            return True
        _debounce_cache[key] = now
        _debounce_cache.move_to_end(key)
        while len(_debounce_cache) > _DEBOUNCE_MAX_ENTRIES:
            _debounce_cache.popitem(last=False)
    return False


def _reset_debounce_cache() -> None:
    """Test helper: drop the in-memory debounce window."""

    with _debounce_lock:
        _debounce_cache.clear()


# ---------------------------------------------------------------------------


def _compose_description(payload: AuditTrackRequest) -> str:
    parts: list[str] = []
    if payload.description:
        parts.append(payload.description.strip())
    if payload.metadata:
        try:
            encoded = json.dumps(payload.metadata, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            encoded = str(payload.metadata)
        parts.append(f"metadata={encoded}")
    return " | ".join(parts)[:2000]


@router.post("/track", response_model=AuditTrackResponse, dependencies=[Depends(require_permission("audit:view"))])
def track_event(
    payload: AuditTrackRequest,
    request: Request,
    context: AuthContext = Depends(get_current_auth_context),
) -> AuditTrackResponse:
    module = payload.module.strip() or "unknown"
    action = payload.action.strip() or "unknown"
    actor_user_id = int(getattr(context.user, "id", 0)) or None

    if _is_duplicate(actor_user_id, module, action):
        return AuditTrackResponse(success=True, throttled=True)

    audit_log_service.record(
        action=action,
        module=module,
        description=_compose_description(payload),
        actor_user_id=actor_user_id,
        ip_address=client_ip(request),
        user_agent=user_agent(request),
        result="success",
    )
    return AuditTrackResponse(success=True, throttled=False)
