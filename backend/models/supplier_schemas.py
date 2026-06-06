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
    created_at: datetime
    updated_at: datetime
