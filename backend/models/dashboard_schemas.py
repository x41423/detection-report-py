"""Pydantic models for Data Dashboard (数据驾驶舱)."""
from __future__ import annotations

from pydantic import BaseModel


class DashboardOverview(BaseModel):
    total_suppliers: int = 0
    active_suppliers: int = 0
    purchase_this_month: float = 0
    orders_this_month: float = 0
    pending_settlements: int = 0
    low_stock_items: int = 0


class MonthlyTrend(BaseModel):
    period: str
    amount: float
    count: int


class TopSupplier(BaseModel):
    supplier_id: int
    supplier_name: str
    total_amount: float
    order_count: int


class DashboardResponse(BaseModel):
    success: bool = True
    overview: DashboardOverview
    purchase_trend: list[MonthlyTrend] = []
    order_trend: list[MonthlyTrend] = []
    top_suppliers: list[TopSupplier] = []
