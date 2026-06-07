"""Order management API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.dependencies import get_current_auth_context, require_permission
from backend.models.order_schemas import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    OrderCopyOptions,
    OrderAfterSaleCreate,
    OrderAfterSaleResponse,
    ColumnPreferenceRequest,
    ColumnPreferenceResponse,
)
from backend.services.order_service import OrderService

router = APIRouter()
service = OrderService()


def _raise(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


# ==================================================================
# Column Preference (static paths BEFORE dynamic /{order_id})
# ==================================================================

@router.put(
    "/column-preference",
    dependencies=[Depends(require_permission("order:view"))],
)
def save_column_preference(req: ColumnPreferenceRequest, context=Depends(get_current_auth_context)):
    try:
        user_id = context.user_id if context else 0
        return service.save_column_preference(user_id, req.page_key, req.visible_columns)
    except Exception as exc:
        _raise(exc)


@router.get(
    "/column-preference",
    dependencies=[Depends(require_permission("order:view"))],
)
def get_column_preference(page_key: str = Query(default="order_list"), context=Depends(get_current_auth_context)):
    try:
        user_id = context.user_id if context else 0
        return service.get_column_preference(user_id, page_key)
    except Exception as exc:
        _raise(exc)


# ==================================================================
# Orders
# ==================================================================

@router.get(
    "/",
    dependencies=[Depends(require_permission("order:view"))],
)
def list_orders(
    search: str = Query(default=""),
    merchant_name: str | None = Query(default=None),
    order_status: str | None = Query(default=None),
    date_mode: str | None = Query(default=None, description="order_date|receipt_date"),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return service.list_orders(
            search=search, merchant_name=merchant_name, order_status=order_status,
            date_mode=date_mode, date_from=date_from, date_to=date_to,
            limit=limit, offset=offset,
        )
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/",
    dependencies=[Depends(require_permission("order:create"))],
)
def create_order(data: OrderCreate):
    try:
        return service.create_order(data)
    except Exception as exc:
        _raise(exc)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:view"))],
)
def get_order(order_id: int):
    try:
        return service.get_order(order_id)
    except LookupError as exc:
        _raise(exc)


@router.put(
    "/{order_id}",
    response_model=OrderResponse,
    dependencies=[Depends(require_permission("order:update"))],
)
def update_order(order_id: int, data: OrderUpdate):
    try:
        return service.update_order(order_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.delete(
    "/{order_id}",
    dependencies=[Depends(require_permission("order:delete"))],
)
def delete_order(order_id: int):
    try:
        return service.delete_order(order_id)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.post(
    "/{order_id}/copy",
    dependencies=[Depends(require_permission("order:copy"))],
)
def copy_order(order_id: int, options: OrderCopyOptions, context=Depends(get_current_auth_context)):
    try:
        operator = context.user.username if context and context.user else None
        return service.copy_order(order_id, options.model_dump(), operator)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.post(
    "/{order_id}/outbound",
    dependencies=[Depends(require_permission("order:update"))],
)
def confirm_order_outbound(order_id: int):
    """确认出库 → 自动同步库存 (OUT)"""
    try:
        return service.confirm_outbound(order_id)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.post(
    "/{order_id}/undo-outbound",
    dependencies=[Depends(require_permission("order:update"))],
)
def undo_order_outbound(order_id: int):
    """撤销出库 → 恢复库存 + 回退订单状态"""
    try:
        return service.undo_outbound(order_id)
    except (LookupError, ValueError) as exc:
        _raise(exc)


# ==================================================================
# After-Sale
# ==================================================================

@router.post(
    "/{order_id}/after-sale",
    dependencies=[Depends(require_permission("order:create"))],
)
def create_after_sale(order_id: int, data: OrderAfterSaleCreate):
    try:
        return service.create_after_sale(order_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.get(
    "/{order_id}/after-sale",
    dependencies=[Depends(require_permission("order:view"))],
)
def list_after_sales(order_id: int):
    try:
        return service.get_after_sales(order_id)
    except LookupError as exc:
        _raise(exc)
