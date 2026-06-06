"""Future reserved endpoints — return 501 Not Implemented."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.dependencies import require_permission
from backend.api.response_utils import future_endpoint

router = APIRouter()


def _future(module: str):
    raise HTTPException(status_code=501, detail=future_endpoint(module))


# ---------------------------------------------------------------------------
# Coupon (优惠券)
# ---------------------------------------------------------------------------

@router.get("/", dependencies=[Depends(require_permission("supplier:view"))])
def future_coupon_list():
    _future("优惠券管理")

@router.post("/", dependencies=[Depends(require_permission("supplier:create"))])
def future_coupon_create():
    _future("优惠券管理")


# ---------------------------------------------------------------------------
# Delivery (配送管理)
# ---------------------------------------------------------------------------

@router.get("/routes", dependencies=[Depends(require_permission("inventory:view"))])
def future_delivery_routes():
    _future("配送路线")

@router.get("/tasks", dependencies=[Depends(require_permission("inventory:view"))])
def future_delivery_tasks():
    _future("配送任务")


# ---------------------------------------------------------------------------
# Sorting (分拣管理)
# ---------------------------------------------------------------------------

@router.get("/sort-tasks", dependencies=[Depends(require_permission("inventory:view"))])
def future_sorting_tasks():
    _future("分拣任务")

@router.get("/performance", dependencies=[Depends(require_permission("inventory:view"))])
def future_sorting_performance():
    _future("分拣绩效")
