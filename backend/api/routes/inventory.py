from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.auth.dependencies import require_permission
from backend.models.schemas import (
    InventoryAdjustmentRequest,
    InventoryBalanceListResponse,
    InventoryDeleteResponse,
    InventoryOutboundRequest,
    InventoryTransactionListResponse,
    InventoryTransactionMutationResponse,
)
from backend.services.inventory_service import InventoryService

router = APIRouter()
service = InventoryService()


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, KeyError):
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/balances", response_model=InventoryBalanceListResponse, dependencies=[Depends(require_permission("inventory:view"))])
def list_inventory_balances(
    search: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=1000),
    include_zero: bool = Query(default=False),
):
    try:
        return InventoryBalanceListResponse(
            **service.list_balances(search=search, limit=limit, include_zero=include_zero)
        )
    except ValueError as exc:
        _raise_http_error(exc)


@router.get(
    "/transactions",
    response_model=InventoryTransactionListResponse,
    dependencies=[Depends(require_permission("inventory:view"))],
)
def list_inventory_transactions(
    search: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    source_type: str | None = Query(default=None),
):
    try:
        return InventoryTransactionListResponse(
            **service.list_transactions(search=search, limit=limit, offset=offset, source_type=source_type)
        )
    except ValueError as exc:
        _raise_http_error(exc)


@router.get("/export/balances", dependencies=[Depends(require_permission("inventory:export"))])
def export_inventory_balances(
    search: str = Query(default=""),
    include_zero: bool = Query(default=False),
):
    try:
        content, filename = service.export_balances_csv(search=search, include_zero=include_zero)
    except ValueError as exc:
        _raise_http_error(exc)

    return StreamingResponse(
        iter([content.encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/outbound", response_model=InventoryTransactionMutationResponse, dependencies=[Depends(require_permission("inventory:create"))])
def create_inventory_outbound(req: InventoryOutboundRequest):
    try:
        return InventoryTransactionMutationResponse(
            **service.create_outbound(
                business_date=req.business_date,
                name=req.name,
                unit=req.unit,
                quantity=req.quantity,
                note=req.note or "",
            )
        )
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.put(
    "/outbound/{transaction_id}",
    response_model=InventoryTransactionMutationResponse,
    dependencies=[Depends(require_permission("inventory:update"))],
)
def update_inventory_outbound(transaction_id: int, req: InventoryOutboundRequest):
    try:
        return InventoryTransactionMutationResponse(
            **service.update_outbound(
                transaction_id,
                business_date=req.business_date,
                name=req.name,
                unit=req.unit,
                quantity=req.quantity,
                note=req.note or "",
            )
        )
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.delete("/outbound/{transaction_id}", response_model=InventoryDeleteResponse, dependencies=[Depends(require_permission("inventory:delete"))])
def delete_inventory_outbound(transaction_id: int):
    try:
        return InventoryDeleteResponse(**service.delete_outbound(transaction_id))
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.post(
    "/adjustments",
    response_model=InventoryTransactionMutationResponse,
    dependencies=[Depends(require_permission("inventory:create"))],
)
def create_inventory_adjustment(req: InventoryAdjustmentRequest):
    try:
        return InventoryTransactionMutationResponse(
            **service.create_adjustment(
                business_date=req.business_date,
                name=req.name,
                unit=req.unit,
                target_quantity=req.target_quantity,
                note=req.note or "",
            )
        )
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.put(
    "/adjustments/{transaction_id}",
    response_model=InventoryTransactionMutationResponse,
    dependencies=[Depends(require_permission("inventory:update"))],
)
def update_inventory_adjustment(transaction_id: int, req: InventoryAdjustmentRequest):
    try:
        return InventoryTransactionMutationResponse(
            **service.update_adjustment(
                transaction_id,
                business_date=req.business_date,
                name=req.name,
                unit=req.unit,
                target_quantity=req.target_quantity,
                note=req.note or "",
            )
        )
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.delete(
    "/adjustments/{transaction_id}",
    response_model=InventoryDeleteResponse,
    dependencies=[Depends(require_permission("inventory:delete"))],
)
def delete_inventory_adjustment(transaction_id: int):
    try:
        return InventoryDeleteResponse(**service.delete_adjustment(transaction_id))
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)
