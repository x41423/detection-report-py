"""Supplier management API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.response_utils import future_endpoint
from backend.auth.dependencies import require_permission
from backend.models.supplier_schemas import SupplierCreate, SupplierResponse, SupplierUpdate
from backend.services.supplier_service import SupplierService

router = APIRouter()
service = SupplierService()


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


@router.get(
    "/",
    dependencies=[Depends(require_permission("supplier:view"))],
)
def list_suppliers(
    search: str = Query(default=""),
    status: str | None = Query(default=None),
    supplier_type: str | None = Query(default=None),
    level: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.list_suppliers(search=search, status=status, supplier_type=supplier_type, level=level, limit=limit, offset=offset)
    except ValueError as exc:
        _raise_http_error(exc)


@router.post(
    "/",
    response_model=SupplierResponse,
    dependencies=[Depends(require_permission("supplier:create"))],
)
def create_supplier(data: SupplierCreate):
    try:
        result = service.create_supplier(data)
        return result["supplier"]
    except ValueError as exc:
        _raise_http_error(exc)


@router.get(
    "/{supplier_id}",
    response_model=SupplierResponse,
    dependencies=[Depends(require_permission("supplier:view"))],
)
def get_supplier(supplier_id: int):
    try:
        return service.get_supplier(supplier_id)
    except (LookupError, ValueError) as exc:
        _raise_http_error(exc)


@router.put(
    "/{supplier_id}",
    response_model=SupplierResponse,
    dependencies=[Depends(require_permission("supplier:edit"))],
)
def update_supplier(supplier_id: int, data: SupplierUpdate):
    try:
        result = service.update_supplier(supplier_id, data)
        return result["supplier"]
    except (LookupError, ValueError) as exc:
        _raise_http_error(exc)


@router.delete(
    "/{supplier_id}",
    dependencies=[Depends(require_permission("supplier:delete"))],
)
def delete_supplier(supplier_id: int):
    try:
        return service.deactivate_supplier(supplier_id)
    except (LookupError, ValueError) as exc:
        _raise_http_error(exc)


# ------------------------------------------------------------------
# FUTURE endpoints (P1 / P2)
# ------------------------------------------------------------------


@router.get("/{supplier_id}/purchase-history")
def supplier_purchase_history(supplier_id: int):
    raise HTTPException(status_code=501, detail=future_endpoint("supplier_purchase_history"))


@router.get("/{supplier_id}/settlement")
def supplier_settlement(supplier_id: int):
    raise HTTPException(status_code=501, detail=future_endpoint("supplier_settlement"))
