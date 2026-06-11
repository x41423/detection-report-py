"""Dashboard API route."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth.dependencies import require_permission
from backend.services.dashboard_service import DashboardService

router = APIRouter()
service = DashboardService()


@router.get(
    "/",
    dependencies=[Depends(require_permission("dashboard:view"))],
)
def get_dashboard():
    """数据驾驶舱：概览、采购/订单趋势、Top供应商"""
    return service.get_dashboard()
