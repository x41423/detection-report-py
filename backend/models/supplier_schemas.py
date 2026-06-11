"""真实供应商（上游供货商）Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    supplier_code: str            # 必填
    name: str                     # 必填
    company_name: str = ""
    contact_address: str = ""
    remark: str = ""
    default_purchaser: str = ""
    linked_station: str = ""
    settlement_cycle: str = "日结"
    invoice_type: str = "普票或无票"
    sales_purchase_settlement: int = 0
    business_license: str = ""
    bank_account_name: str = ""
    bank_name: str = ""
    bank_account: str = ""
    supplier_nature: str = "普通"
    purchase_auto_sync: int = 0
    geo_location: str = ""
    qualification_images: str = "[]"
    payment_qr: str = ""


class SupplierUpdate(BaseModel):
    supplier_code: str | None = None
    name: str | None = None
    company_name: str | None = None
    contact_address: str | None = None
    remark: str | None = None
    default_purchaser: str | None = None
    settlement_cycle: str | None = None
    invoice_type: str | None = None
    sales_purchase_settlement: int | None = None
    business_license: str | None = None
    bank_account_name: str | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    supplier_nature: str | None = None
    purchase_auto_sync: int | None = None
    geo_location: str | None = None
    qualification_images: str | None = None
    payment_qr: str | None = None


class SupplierResponse(BaseModel):
    id: int
    supplier_code: str
    name: str
    company_name: str
    contact_address: str
    remark: str
    default_purchaser: str
    linked_station: str
    settlement_cycle: str
    invoice_type: str
    sales_purchase_settlement: int
    business_license: str
    bank_account_name: str
    bank_name: str
    bank_account: str
    supplier_nature: str
    purchase_auto_sync: int
    geo_location: str
    qualification_images: str
    payment_qr: str
    status: str
    created_at: str
    updated_at: str
