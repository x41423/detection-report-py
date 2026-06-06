"""Loss/overflow report routes — master-detail pattern."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.db.store import get_connection
from backend.auth.dependencies import require_permission

router = APIRouter()


# ---- Schemas ----

class LossItemIn(BaseModel):
    product_id: int
    quantity: float
    unit_name: str = ""
    reason: str = ""
    unit_price: float = 0
    amount: float = 0


class LossReportCreate(BaseModel):
    report_no: str = ""
    report_date: str
    report_type: str = "loss"
    warehouse_id: int = 0
    notes: str = ""
    items: list[LossItemIn] = []


class LossReportUpdate(BaseModel):
    report_date: str | None = None
    report_type: str | None = None
    notes: str | None = None
    status: str | None = None


# ---- Routes ----

@router.get("/", dependencies=[Depends(require_permission("inventory:view"))])
def list_reports(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    conn = get_connection()
    cur = conn.execute("SELECT COUNT(*) FROM LossReport")
    total = cur.fetchone()[0]
    cur = conn.execute("SELECT * FROM LossReport ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"success": True, "items": rows, "total": total}


@router.get("/{rid}", dependencies=[Depends(require_permission("inventory:view"))])
def get_report(rid: int):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM LossReport WHERE id=?", (rid,))
    report = cur.fetchone()
    if not report:
        conn.close()
        raise HTTPException(404, "报损报溢单不存在")
    cur = conn.execute("SELECT * FROM LossReportItem WHERE report_id=? ORDER BY id", (rid,))
    items = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"success": True, "report": dict(report), "items": items}


@router.post("/", dependencies=[Depends(require_permission("inventory:create"))])
def create_report(body: LossReportCreate):
    conn = get_connection()
    # generate report_no if empty
    rno = body.report_no or _next_report_no(conn)
    cur = conn.execute("""
        INSERT INTO LossReport (report_no, report_date, report_type, warehouse_id, notes, status)
        VALUES (?, ?, ?, ?, ?, 'draft')
    """, (rno, body.report_date, body.report_type, body.warehouse_id, body.notes))
    rid = cur.lastrowid
    total_amount = 0.0
    for item in body.items:
        amt = item.quantity * item.unit_price if item.amount == 0 else item.amount
        conn.execute("""
            INSERT INTO LossReportItem (report_id, product_id, quantity, unit_name, reason, unit_price, amount)
            VALUES (?,?,?,?,?,?,?)
        """, (rid, item.product_id, item.quantity, item.unit_name, item.reason, item.unit_price, amt))
        total_amount += amt
    conn.execute("UPDATE LossReport SET total_amount=? WHERE id=?", (total_amount, rid))
    conn.commit()
    conn.close()
    return {"success": True, "message": "已创建", "id": rid}


@router.put("/{rid}", dependencies=[Depends(require_permission("inventory:edit"))])
def update_report(rid: int, body: LossReportUpdate):
    conn = get_connection()
    cur = conn.execute("SELECT id FROM LossReport WHERE id=?", (rid,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "报损报溢单不存在")
    fields = []
    vals = []
    for k in ("report_date", "report_type", "notes", "status"):
        v = getattr(body, k, None)
        if v is not None:
            fields.append(f"{k}=?")
            vals.append(v)
    if fields:
        vals.append(rid)
        conn.execute(f"UPDATE LossReport SET {','.join(fields)}, updated_at=CURRENT_TIMESTAMP WHERE id=?", vals)
        conn.commit()
    conn.close()
    return {"success": True, "message": "已更新"}


@router.delete("/{rid}", dependencies=[Depends(require_permission("inventory:create"))])
def delete_report(rid: int):
    conn = get_connection()
    cur = conn.execute("SELECT id FROM LossReport WHERE id=?", (rid,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(404, "报损报溢单不存在")
    conn.execute("DELETE FROM LossReportItem WHERE report_id=?", (rid,))
    conn.execute("DELETE FROM LossReport WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "已删除"}


def _next_report_no(conn) -> str:
    from datetime import date
    prefix = f"LR{date.today().strftime('%Y%m%d')}"
    cur = conn.execute("SELECT COUNT(*) FROM LossReport WHERE report_no LIKE ?", (prefix + "%",))
    n = cur.fetchone()[0] + 1
    return f"{prefix}{n:03d}"
