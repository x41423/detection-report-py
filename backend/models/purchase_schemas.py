"""Pydantic models for Purchase In / Return modules."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Purchase In — Item
# ---------------------------------------------------------------------------


class PurchaseInItemCreate(BaseModel):
    veg_name: str = Field(..., min_length=1, max_length=200)
    category: str | None = None
    unit: str = Field(default="斤")
    quantity: float = Field(default=0, ge=0)
    unit_price: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0, ge=0)


class PurchaseInItemResponse(BaseModel):
    id: int
    veg_name: str
    category: str | None
    unit: str
    quantity: float
    unit_price: float
    amount: float
    tax_rate: float


# ---------------------------------------------------------------------------
# Purchase In — Record
# ---------------------------------------------------------------------------


class PurchaseInCreate(BaseModel):
    supplier_id: int
    inbound_date: str = Field(..., description="YYYY-MM-DD")
    remark: str | None = None
    items: list[PurchaseInItemCreate] = Field(default_factory=list)


class PurchaseInUpdate(BaseModel):
    inbound_date: str | None = None
    remark: str | None = None


class PurchaseInResponse(BaseModel):
    id: int
    order_no: str
    supplier_id: int
    inbound_date: str
    total_amount: float
    status: str
    remark: str | None
    operator: str | None
    items: list[PurchaseInItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Purchase Return — Item
# ---------------------------------------------------------------------------


class PurchaseReturnItemCreate(BaseModel):
    veg_name: str = Field(..., min_length=1, max_length=200)
    category: str | None = None
    unit: str = Field(default="斤")
    quantity: float = Field(default=0, ge=0)
    unit_price: float = Field(default=0, ge=0)


class PurchaseReturnItemResponse(BaseModel):
    id: int
    veg_name: str
    category: str | None
    unit: str
    quantity: float
    unit_price: float
    amount: float


# ---------------------------------------------------------------------------
# Purchase Return — Record
# ---------------------------------------------------------------------------


class PurchaseReturnCreate(BaseModel):
    supplier_id: int
    return_date: str = Field(..., description="YYYY-MM-DD")
    remark: str | None = None
    items: list[PurchaseReturnItemCreate] = Field(default_factory=list)


class PurchaseReturnUpdate(BaseModel):
    return_date: str | None = None
    remark: str | None = None


class PurchaseReturnResponse(BaseModel):
    id: int
    order_no: str
    supplier_id: int
    return_date: str
    total_amount: float
    status: str
    remark: str | None
    operator: str | None
    items: list[PurchaseReturnItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
