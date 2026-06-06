"""Pydantic models for Quotation management (报价单管理)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Quotation
# ---------------------------------------------------------------------------


class QuotationCreate(BaseModel):
    """新建报价单 — 对齐观麦「新建报价单」表单。"""

    name: str = Field(..., min_length=1, max_length=200)
    external_name: str = Field(default="", max_length=20)
    currency: str = Field(default="人民币")
    operation_time: str = Field(default="默认运营时间")
    tags: str = Field(default="")
    status: str = Field(default="active")
    pricing_start_date: str = Field(default="")
    pricing_end_date: str = Field(default="")
    auto_pricing: bool = Field(default=False)
    description: str = Field(default="")
    products: list["QuotationProductCreate"] = Field(default_factory=list)


class QuotationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    external_name: str | None = Field(default=None, max_length=20)
    currency: str | None = None
    operation_time: str | None = None
    tags: str | None = None
    status: str | None = None
    pricing_start_date: str | None = None
    pricing_end_date: str | None = None
    auto_pricing: bool | None = None
    description: str | None = None


class QuotationResponse(BaseModel):
    id: int
    code: str
    name: str
    external_name: str
    currency: str
    operation_time: str
    tags: str
    status: str
    pricing_start_date: str
    pricing_end_date: str
    auto_pricing: int
    description: str
    product_count: int = 0
    products: list["QuotationProductResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Quotation → Product (N:M)
# ---------------------------------------------------------------------------


class QuotationProductCreate(BaseModel):
    product_id: int
    price: float = Field(default=0, ge=0)


class QuotationProductUpdate(BaseModel):
    price: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class QuotationProductResponse(BaseModel):
    id: int
    quotation_id: int
    product_id: int
    product_name: str = ""
    product_code: str = ""
    base_unit: str = ""
    price: float
    is_active: int
