"""Product sales analysis routes — aggregated sales data."""

from __future__ import annotations

import csv, io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.db.product_analysis_repository import ProductAnalysisRepository as Repo
from backend.auth.dependencies import require_permission

router = APIRouter()


@router.get("/product-sales/summary", dependencies=[Depends(require_permission("inventory:view"))])
def product_sales_summary(date_from: str = Query(default=""), date_to: str = Query(default="")):
    return {"success": True, "data": Repo.summary(date_from=date_from, date_to=date_to)}


@router.get("/product-sales/top", dependencies=[Depends(require_permission("inventory:view"))])
def product_sales_top(date_from: str = Query(default=""), date_to: str = Query(default=""), limit: int = Query(default=20, ge=1, le=100)):
    return {"success": True, "items": Repo.top_products(date_from=date_from, date_to=date_to, limit=limit)}


@router.get("/product-sales/by-category", dependencies=[Depends(require_permission("inventory:view"))])
def product_sales_by_category(date_from: str = Query(default=""), date_to: str = Query(default="")):
    return {"success": True, "items": Repo.by_category(date_from=date_from, date_to=date_to)}


# ── Sales report (P2.3) ─────────────────────────────────────────────

@router.get("/sales-report/orders", dependencies=[Depends(require_permission("inventory:view"))])
def sales_report_orders(
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    items = Repo.orders_by_date(date_from=date_from, date_to=date_to, limit=limit, offset=offset)
    total = Repo.orders_count(date_from=date_from, date_to=date_to)
    return {"success": True, "items": items, "total": total}


@router.get("/sales-report/export", dependencies=[Depends(require_permission("inventory:view"))])
def sales_report_export(date_from: str = Query(default=""), date_to: str = Query(default="")):
    items = Repo.orders_by_date(date_from=date_from, date_to=date_to, limit=10000, offset=0)
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["订单号", "日期", "商户", "下单金额", "销售额(含运费)", "运费", "优惠", "状态"])
    for r in items:
        w.writerow([r["order_no"], r["order_date"], r["merchant_name"], r["order_amount"],
                     r["sales_amount_incl_freight"], r["freight"], r["discount_amount"], r["order_status"]])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=sales-report.csv"})


# ── Customer analysis (P2.4) ─────────────────────────────────────────

@router.get("/customer/summary", dependencies=[Depends(require_permission("inventory:view"))])
def customer_summary(date_from: str = Query(default=""), date_to: str = Query(default="")):
    return {"success": True, "data": Repo.customer_summary(date_from=date_from, date_to=date_to)}


@router.get("/customer/ranking", dependencies=[Depends(require_permission("inventory:view"))])
def customer_ranking(date_from: str = Query(default=""), date_to: str = Query(default=""), limit: int = Query(default=30, ge=1, le=200)):
    return {"success": True, "items": Repo.customer_ranking(date_from=date_from, date_to=date_to, limit=limit)}


# ── Inventory summary (P2.5) ─────────────────────────────────────────

@router.get("/inventory/summary", dependencies=[Depends(require_permission("inventory:view"))])
def inv_summary(date_from: str = Query(default=""), date_to: str = Query(default="")):
    return {"success": True, "data": Repo.inventory_summary(date_from=date_from, date_to=date_to)}


@router.get("/inventory/by-source", dependencies=[Depends(require_permission("inventory:view"))])
def inv_by_source(date_from: str = Query(default=""), date_to: str = Query(default="")):
    return {"success": True, "items": Repo.inventory_by_source(date_from=date_from, date_to=date_to)}


# ── Payables (P2.6) ──────────────────────────────────────────────────

@router.get("/payables", dependencies=[Depends(require_permission("inventory:view"))])
def payables(supplier_id: int = Query(default=0)):
    return {"success": True, "items": Repo.payables_by_supplier(supplier_id=supplier_id)}


# ── Inactive merchants (P2.11) ───────────────────────────────────────

@router.get("/inactive-merchants", dependencies=[Depends(require_permission("inventory:view"))])
def inactive_merchants(days: int = Query(default=7, ge=1, le=90)):
    return {"success": True, "items": Repo.inactive_merchants(days=days)}
