"""Purchase In / Return API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import require_permission
from backend.models.purchase_schemas import (
    PurchaseInCreate,
    PurchaseInResponse,
    PurchaseInUpdate,
    PurchaseReturnCreate,
    PurchaseReturnResponse,
    PurchaseReturnUpdate,
)
from backend.services.purchase_service import PurchaseService

router = APIRouter()
service = PurchaseService()


def _raise(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


# ==================================================================
# Purchase In
# ==================================================================

@router.get(
    "/in",
    dependencies=[Depends(require_permission("purchase:view"))],
)
def list_purchase_in(
    search: str = Query(default=""),
    supplier_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.list_in(
            search=search, supplier_id=supplier_id, status=status,
            limit=limit, offset=offset,
        )
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/in",
    response_model=PurchaseInResponse,
    dependencies=[Depends(require_permission("purchase:create"))],
)
def create_purchase_in(data: PurchaseInCreate):
    try:
        result = service.create_in(data)
        return result["record"]
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.get(
    "/in/{record_id}",
    response_model=PurchaseInResponse,
    dependencies=[Depends(require_permission("purchase:view"))],
)
def get_purchase_in(record_id: int):
    try:
        return service.get_in(record_id)
    except LookupError as exc:
        _raise(exc)


@router.put(
    "/in/{record_id}",
    response_model=PurchaseInResponse,
    dependencies=[Depends(require_permission("purchase:update"))],
)
def update_purchase_in(record_id: int, data: PurchaseInUpdate):
    try:
        return service.update_in(record_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.post(
    "/in/{record_id}/confirm",
    dependencies=[Depends(require_permission("purchase:update"))],
)
def confirm_purchase_in(record_id: int):
    """确认入库 → 自动同步库存 (IN)"""
    try:
        return service.confirm_in(record_id)
    except (LookupError, ValueError) as exc:
        _raise(exc)


# ==================================================================
# Purchase Return
# ==================================================================

@router.get(
    "/return",
    dependencies=[Depends(require_permission("purchase:view"))],
)
def list_purchase_return(
    search: str = Query(default=""),
    supplier_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.list_return(
            search=search, supplier_id=supplier_id, status=status,
            limit=limit, offset=offset,
        )
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/return",
    response_model=PurchaseReturnResponse,
    dependencies=[Depends(require_permission("purchase:create"))],
)
def create_purchase_return(data: PurchaseReturnCreate):
    try:
        result = service.create_return(data)
        return result["record"]
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.get(
    "/return/{record_id}",
    response_model=PurchaseReturnResponse,
    dependencies=[Depends(require_permission("purchase:view"))],
)
def get_purchase_return(record_id: int):
    try:
        return service.get_return(record_id)
    except LookupError as exc:
        _raise(exc)


@router.post(
    "/return/{record_id}/confirm",
    dependencies=[Depends(require_permission("purchase:update"))],
)
def confirm_purchase_return(record_id: int):
    """确认退货 → 自动同步库存 (OUT)"""
    try:
        return service.confirm_return(record_id)
    except (LookupError, ValueError) as exc:
        _raise(exc)
