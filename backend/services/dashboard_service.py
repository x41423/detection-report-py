"""Dashboard read-only service."""
from __future__ import annotations

from datetime import date
from typing import Any

from app.db.dashboard_repository import DashboardRepository
from backend.models.dashboard_schemas import DashboardResponse


class DashboardService:
    def __init__(self) -> None:
        pass

    def get_dashboard(self) -> dict[str, Any]:
        today = date.today()
        current_month = today.strftime("%Y-%m")

        overview = DashboardRepository.get_overview(current_month)
        purchase_trend = DashboardRepository.get_purchase_trend()
        order_trend = DashboardRepository.get_order_trend()
        top_suppliers = DashboardRepository.get_top_suppliers()

        return DashboardResponse(
            overview=overview,
            purchase_trend=[
                {"period": r["period"], "amount": r["amount"], "count": r["count"]}
                for r in purchase_trend
            ],
            order_trend=[
                {"period": r["period"], "amount": r["amount"], "count": r["count"]}
                for r in order_trend
            ],
            top_suppliers=[
                {
                    "supplier_id": r["supplier_id"],
                    "supplier_name": r["supplier_name"],
                    "total_amount": r["total_amount"],
                    "order_count": r["order_count"],
                }
                for r in top_suppliers
            ],
        ).model_dump()
