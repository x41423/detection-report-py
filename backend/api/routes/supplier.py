"""Supplier API routes — 真实供应商（上游供货商）管理."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import require_permission
from backend.models.supplier_schemas import SupplierCreate, SupplierUpdate
from backend.services.supplier_service import SupplierService

router = APIRouter()
service = SupplierService()


@router.get("/", dependencies=[Depends(require_permission("supplier:view"))])
def list_suppliers(
    search: str = Query(default=""),
    status: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return service.list(search=search, status=status, limit=limit, offset=offset)


@router.get("/{sid}", dependencies=[Depends(require_permission("supplier:view"))])
def get_supplier(sid: int):
    result = service.get(sid)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.post("/", dependencies=[Depends(require_permission("supplier:create"))])
def create_supplier(data: SupplierCreate):
    return service.create(data)


@router.put("/{sid}", dependencies=[Depends(require_permission("supplier:update"))])
def update_supplier(sid: int, data: SupplierUpdate):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    result = service.update(sid, updates)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.delete("/{sid}", dependencies=[Depends(require_permission("supplier:delete"))])
def delete_supplier(sid: int):
    return service.delete(sid)
