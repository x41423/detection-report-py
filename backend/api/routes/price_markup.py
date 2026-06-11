"""Price markup routes — simple CRUD over PriceMarkup table."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.crud_helpers import simple_create, simple_delete, simple_list, simple_update
from backend.auth.dependencies import require_permission

router = APIRouter()

TABLE = "PriceMarkup"
COLS = ("name", "rate", "scope", "scope_id", "is_active")


class MarkupCreate(BaseModel):
    name: str = ""
    rate: float = 0
    scope: str = "global"
    scope_id: int = 0


class MarkupUpdate(BaseModel):
    name: str | None = None
    rate: float | None = None
    scope: str | None = None
    scope_id: int | None = None
    is_active: int | None = None


@router.get("/", dependencies=[Depends(require_permission("price_markup:view"))])
def list_markups(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    items = simple_list(TABLE, limit, offset)
    total = len(simple_list(TABLE, 1000, 0))
    return {"success": True, "items": items, "total": total}


@router.post("/", dependencies=[Depends(require_permission("price_markup:create"))])
def create_markup(body: MarkupCreate):
    mid = simple_create(TABLE, COLS, body.model_dump())
    return {"success": True, "message": "已创建", "id": mid}


@router.put("/{mid}", dependencies=[Depends(require_permission("price_markup:update"))])
def update_markup(mid: int, body: MarkupUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(400, "没有要更新的字段")
    ok = simple_update(TABLE, mid, COLS, data)
    if not ok:
        raise HTTPException(404, "规则不存在")
    return {"success": True, "message": "已更新"}


@router.delete("/{mid}", dependencies=[Depends(require_permission("price_markup:delete"))])
def delete_markup(mid: int):
    ok = simple_delete(TABLE, mid)
    if not ok:
        raise HTTPException(404, "规则不存在")
    return {"success": True, "message": "已删除"}
