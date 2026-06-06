"""Price Lock API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import require_permission
from backend.models.price_lock_schemas import (
    PriceLockCreate,
    PriceLockResponse,
    PriceLockUpdate,
)
from backend.services.price_lock_service import PriceLockService

router = APIRouter()
service = PriceLockService()


def _raise(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/", dependencies=[Depends(require_permission("supplier:view"))])
def list_rules(
    search: str = Query(default=""),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.list_rules(search=search, status=status, limit=limit, offset=offset)
    except ValueError as exc:
        _raise(exc)


@router.post("/", response_model=PriceLockResponse, dependencies=[Depends(require_permission("supplier:create"))])
def create_rule(data: PriceLockCreate):
    try:
        result = service.create(data)
        return result["record"]
    except Exception as exc:
        _raise(exc)


@router.get("/{rule_id}", response_model=PriceLockResponse, dependencies=[Depends(require_permission("supplier:view"))])
def get_rule(rule_id: int):
    try:
        return service.get(rule_id)
    except LookupError as exc:
        _raise(exc)


@router.put("/{rule_id}", response_model=PriceLockResponse, dependencies=[Depends(require_permission("supplier:edit"))])
def update_rule(rule_id: int, data: PriceLockUpdate):
    try:
        return service.update(rule_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.delete("/{rule_id}", dependencies=[Depends(require_permission("supplier:edit"))])
def deactivate_rule(rule_id: int):
    try:
        return service.deactivate(rule_id)
    except LookupError as exc:
        _raise(exc)
