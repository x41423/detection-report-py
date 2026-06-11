"""Supplier Settlement API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import require_permission
from backend.models.settlement_schemas import (
    SettlementCreate,
    SettlementResponse,
    SettlementUpdate,
)
from backend.services.settlement_service import SettlementService

router = APIRouter()
service = SettlementService()


def _raise(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/",
    dependencies=[Depends(require_permission("settlement:view"))],
)
def list_settlements(
    supplier_id: int | None = Query(default=None),
    period: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.list_settlements(
            supplier_id=supplier_id, period=period, status=status,
            limit=limit, offset=offset,
        )
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/",
    response_model=SettlementResponse,
    dependencies=[Depends(require_permission("settlement:create"))],
)
def create_settlement(data: SettlementCreate):
    try:
        result = service.create(data)
        return result["record"]
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.post(
    "/auto",
    dependencies=[Depends(require_permission("settlement:create"))],
)
def auto_create_settlement(
    supplier_id: int = Query(...),
    period: str = Query(..., description="YYYY-MM"),
):
    """根据已确认的采购入库记录自动生成结算单"""
    try:
        return service.auto_create(supplier_id, period)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.get(
    "/{settlement_id}",
    response_model=SettlementResponse,
    dependencies=[Depends(require_permission("settlement:view"))],
)
def get_settlement(settlement_id: int):
    try:
        return service.get(settlement_id)
    except LookupError as exc:
        _raise(exc)


@router.put(
    "/{settlement_id}",
    response_model=SettlementResponse,
    dependencies=[Depends(require_permission("settlement:update"))],
)
def update_settlement(settlement_id: int, data: SettlementUpdate):
    try:
        return service.update(settlement_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.post(
    "/{settlement_id}/confirm",
    dependencies=[Depends(require_permission("settlement:update"))],
)
def confirm_settlement(settlement_id: int):
    try:
        return service.confirm(settlement_id)
    except (LookupError, ValueError) as exc:
        _raise(exc)
