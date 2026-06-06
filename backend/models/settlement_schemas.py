"""Pydantic models for Supplier Settlement (供应商结算)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SettlementCreate(BaseModel):
    supplier_id: int
    settlement_period: str = Field(..., description="eg. 2026-05")
    payable_amount: float = Field(default=0, ge=0)
    paid_amount: float = Field(default=0, ge=0)
    fee_amount: float = Field(default=0, ge=0)
    discount_amount: float = Field(default=0, ge=0)
    remark: str | None = None


class SettlementUpdate(BaseModel):
    paid_amount: float | None = None
    fee_amount: float | None = None
    discount_amount: float | None = None
    remark: str | None = None


class SettlementResponse(BaseModel):
    id: int
    supplier_id: int
    supplier_name: str | None = None
    settlement_period: str
    payable_amount: float
    paid_amount: float
    fee_amount: float
    discount_amount: float
    balance_amount: float
    reconciliation_status: str
    status: str
    remark: str | None
    operator: str | None
    created_at: datetime
    updated_at: datetime
