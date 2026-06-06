"""Supplier-product price agreement routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.crud_helpers import simple_create, simple_delete, simple_list, simple_update
from backend.auth.dependencies import require_permission

router = APIRouter()

TABLE = "SupplierProductPrice"
COLS = ("supplier_id", "product_id", "price", "unit_name", "effective_from", "effective_to", "is_active")


class AgreementCreate(BaseModel):
    supplier_id: int
    product_id: int
    price: float = 0
    unit_name: str = ""
    effective_from: str = ""
    effective_to: str = ""


class AgreementUpdate(BaseModel):
    supplier_id: int | None = None
    product_id: int | None = None
    price: float | None = None
    unit_name: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    is_active: int | None = None


@router.get("/", dependencies=[Depends(require_permission("supplier:view"))])
def list_agreements(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    items = simple_list(TABLE, limit, offset)
    total = len(simple_list(TABLE, 1000, 0))
    return {"success": True, "items": items, "total": total}


@router.post("/", dependencies=[Depends(require_permission("supplier:create"))])
def create_agreement(body: AgreementCreate):
    aid = simple_create(TABLE, COLS, body.model_dump())
    return {"success": True, "message": "已创建", "id": aid}


@router.put("/{aid}", dependencies=[Depends(require_permission("supplier:edit"))])
def update_agreement(aid: int, body: AgreementUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, "没有要更新的字段")
    ok = simple_update(TABLE, aid, COLS, data)
    if not ok:
        raise HTTPException(404, "协议不存在")
    return {"success": True, "message": "已更新"}


@router.delete("/{aid}", dependencies=[Depends(require_permission("supplier:delete"))])
def delete_agreement(aid: int):
    ok = simple_delete(TABLE, aid)
    if not ok:
        raise HTTPException(404, "协议不存在")
    return {"success": True, "message": "已删除"}
