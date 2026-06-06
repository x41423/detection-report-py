"""Quotation management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import require_permission
from backend.models.quotation_schemas import (
    QuotationCreate,
    QuotationUpdate,
    QuotationProductCreate,
    QuotationProductUpdate,
)
from backend.services.quotation_service import QuotationService

router = APIRouter()
service = QuotationService()


def _raise(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


# ==================================================================
# Quotation
# ==================================================================


@router.get(
    "/",
    dependencies=[Depends(require_permission("quotation:view"))],
)
def list_quotations(
    search: str = Query(default=""),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.list_quotations(
            search=search, status=status, limit=limit, offset=offset,
        )
    except ValueError as exc:
        _raise(exc)


@router.get(
    "/{quotation_id}",
    dependencies=[Depends(require_permission("quotation:view"))],
)
def get_quotation(quotation_id: int):
    try:
        return service.get_quotation(quotation_id)
    except LookupError as exc:
        _raise(exc)


@router.post(
    "/",
    dependencies=[Depends(require_permission("quotation:create"))],
)
def create_quotation(data: QuotationCreate):
    try:
        return service.create_quotation(data)
    except Exception as exc:
        _raise(exc)


@router.put(
    "/{quotation_id}",
    dependencies=[Depends(require_permission("quotation:update"))],
)
def update_quotation(quotation_id: int, data: QuotationUpdate):
    try:
        return service.update_quotation(quotation_id, data)
    except LookupError as exc:
        _raise(exc)


@router.post(
    "/{quotation_id}/toggle",
    dependencies=[Depends(require_permission("quotation:update"))],
)
def toggle_status(quotation_id: int, status: str = Query(default="active")):
    try:
        return service.toggle_status(quotation_id, status)
    except LookupError as exc:
        _raise(exc)


# ==================================================================
# Quotation ↔ Product
# ==================================================================


@router.post(
    "/{quotation_id}/products",
    dependencies=[Depends(require_permission("quotation:create"))],
)
def add_product(quotation_id: int, data: QuotationProductCreate):
    try:
        return service.add_product(quotation_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.put(
    "/products/{qp_id}",
    dependencies=[Depends(require_permission("quotation:update"))],
)
def update_quotation_product(qp_id: int, data: QuotationProductUpdate):
    try:
        return service.update_product(qp_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.delete(
    "/products/{qp_id}",
    dependencies=[Depends(require_permission("quotation:update"))],
)
def remove_quotation_product(qp_id: int):
    try:
        return service.remove_product(qp_id)
    except LookupError as exc:
        _raise(exc)
