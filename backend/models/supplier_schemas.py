"""Pydantic models for the Supplier management module."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    """Fields accepted when creating a new supplier."""

    name: str = Field(..., min_length=1, max_length=200, description="供应商名称")
    contact_person: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_address: str | None = Field(default=None)
    supplier_type: str = Field(default="enterprise", description="供应商类型: individual/enterprise/cooperative")
    business_license: str | None = Field(default=None, max_length=50)
    tax_number: str | None = Field(default=None, max_length=50)
    bank_name: str | None = Field(default=None, max_length=100)
    bank_account: str | None = Field(default=None, max_length=50)
    settlement_method: str = Field(default="monthly", description="结算方式: monthly/weekly/daily")
    payment_terms: str | None = Field(default=None, max_length=100)
    credit_limit: float = Field(default=0, ge=0)
    level: str = Field(default="normal", description="供应商等级: vip/normal/temporary")
    # ── 结算配置（融合观麦模式）──
    settlement_person: str | None = Field(default=None, max_length=100)
    settlement_phone: str | None = Field(default=None, max_length=20)
    date_dimension: str = Field(default="order_date", description="日期维度: order_date/receipt_date")
    period_start_day: int = Field(default=1, ge=1, le=31)
    settlement_day: int = Field(default=1, ge=1, le=31)
    freeze_status: int = Field(default=0, ge=0, le=1)
    approval_status: int = Field(default=1, ge=0, le=1)
    sorting_priority: int = Field(default=0, ge=0, le=9999)
    remark: str | None = Field(default=None)


class SupplierUpdate(BaseModel):
    """Fields accepted when updating an existing supplier — all optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_person: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_address: str | None = Field(default=None)
    supplier_type: str | None = Field(default=None)
    business_license: str | None = Field(default=None, max_length=50)
    tax_number: str | None = Field(default=None, max_length=50)
    bank_name: str | None = Field(default=None, max_length=100)
    bank_account: str | None = Field(default=None, max_length=50)
    settlement_method: str | None = Field(default=None)
    payment_terms: str | None = Field(default=None, max_length=100)
    credit_limit: float | None = Field(default=None, ge=0)
    level: str | None = Field(default=None)
    status: str | None = Field(default=None)
    remark: str | None = Field(default=None)
    # ── 结算配置 ──
    settlement_person: str | None = Field(default=None, max_length=100)
    settlement_phone: str | None = Field(default=None, max_length=20)
    date_dimension: str | None = Field(default=None)
    period_start_day: int | None = Field(default=None, ge=1, le=31)
    settlement_day: int | None = Field(default=None, ge=1, le=31)
    freeze_status: int | None = Field(default=None, ge=0, le=1)
    approval_status: int | None = Field(default=None, ge=0, le=1)
    sorting_priority: int | None = Field(default=None, ge=0, le=9999)


class SupplierResponse(BaseModel):
    """Full supplier record returned by the API."""

    id: int
    code: str
    name: str
    contact_person: str | None
    contact_phone: str | None
    contact_address: str | None
    supplier_type: str
    business_license: str | None
    tax_number: str | None
    bank_name: str | None
    bank_account: str | None
    settlement_method: str
    payment_terms: str | None
    credit_limit: float
    level: str
    status: str
    remark: str | None
    # ── 结算配置 ──
    settlement_person: str | None
    settlement_phone: str | None
    date_dimension: str
    period_start_day: int
    settlement_day: int
    freeze_status: int
    approval_status: int
    sorting_priority: int
    # ── 元数据 ──
    created_at: datetime
    updated_at: datetime


class SupplierTransactionSummary(BaseModel):
    """Supplier transaction overview (similar to 观麦 交易情况 tab)."""

    total_sales_amount: float = 0
    total_sales_amount_excl_freight: float = 0
    total_gross_margin: float = 0
    gross_margin_rate: float = 0
    total_discount: float = 0
    order_count: int = 0
    after_sale_count: int = 0
    abnormal_amount: float = 0
    should_refund: float = 0
    actual_refund: float = 0
