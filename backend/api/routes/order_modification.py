"""Order modification audit routes — submit / review workflow."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.crud_helpers import simple_create, simple_list, simple_update
from backend.auth.dependencies import require_permission

router = APIRouter()

TABLE = "OrderModification"
COLS = ("order_id", "order_no", "modifier_name", "summary", "status", "reviewer_name", "review_comment")


class ModificationCreate(BaseModel):
    order_id: int
    order_no: str = ""
    modifier_name: str = ""
    summary: str = ""


@router.get("/", dependencies=[Depends(require_permission("order:view"))])
def list_modifications(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
                       status: str = Query(default="")):
    where = "1=1"
    params: list = []
    if status.strip():
        where += " AND status=?"
        params.append(status.strip())
    items = simple_list(TABLE, limit, offset, where=where, params=tuple(params))
    total = len(simple_list(TABLE, 1000, 0, where=where, params=tuple(params)))
    return {"success": True, "items": items, "total": total}


@router.post("/", dependencies=[Depends(require_permission("order:create"))])
def create_modification(body: ModificationCreate):
    mid = simple_create(TABLE, COLS, {**body.model_dump(), "status": "pending"})
    return {"success": True, "message": "已提交审核", "id": mid}


@router.put("/{mid}/approve", dependencies=[Depends(require_permission("order:edit"))])
def approve_modification(mid: int, reviewer_name: str = Query(default=""), comment: str = Query(default="")):
    ok = simple_update(TABLE, mid, COLS,
                       {"status": "approved", "reviewer_name": reviewer_name, "review_comment": comment})
    if not ok:
        raise HTTPException(404, "审核记录不存在")
    return {"success": True, "message": "已通过"}


@router.put("/{mid}/reject", dependencies=[Depends(require_permission("order:edit"))])
def reject_modification(mid: int, reviewer_name: str = Query(default=""), comment: str = Query(default="")):
    ok = simple_update(TABLE, mid, COLS,
                       {"status": "rejected", "reviewer_name": reviewer_name, "review_comment": comment})
    if not ok:
        raise HTTPException(404, "审核记录不存在")
    return {"success": True, "message": "已驳回"}
