"""Inventory extension routes — alerts, cross-table transaction summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import require_permission
from backend.services.inventory_report_service import InventoryReportService

router = APIRouter()
service = InventoryReportService()


def _raise(exc: Exception) -> None:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/alerts",
    dependencies=[Depends(require_permission("inventory:view"))],
)
def get_stock_alerts(
    threshold: float = Query(default=10.0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """低库存预警：可用量 <= threshold 的商品"""
    try:
        return service.get_stock_alerts(threshold=threshold, limit=limit)
    except Exception as exc:
        _raise(exc)


@router.get(
    "/summary",
    dependencies=[Depends(require_permission("inventory:view"))],
)
def get_transaction_summary(
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """交易明细汇总（含供应商名称、关联单号），跨 InventoryTransaction + PurchaseIn/Return + Supplier"""
    try:
        return service.get_transaction_summary(
            start_date=start_date, end_date=end_date,
            limit=limit, offset=offset,
        )
    except Exception as exc:
        _raise(exc)
