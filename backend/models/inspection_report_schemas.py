"""Inspection report archive — Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Product sub-model (N:M)
# ---------------------------------------------------------------------------

class InspectionReportProductCreate(BaseModel):
    sku_id: int = 0
    product_id: int = 0
    batch: str = ""


class InspectionReportProductResponse(BaseModel):
    id: int
    report_id: int
    sku_id: int
    product_id: int
    batch: str
    product_name: str = ""
    product_code: str = ""
    sku_name: str = ""


# ---------------------------------------------------------------------------
# Main CRUD
# ---------------------------------------------------------------------------

class InspectionReportCreate(BaseModel):
    name: str = ""
    test_date: str = ""
    valid_from: str = ""
    valid_until: str = ""
    supplier_id: int = 0
    submit_org: str = ""
    test_org: str = ""
    file_url: str = ""
    status: str = "draft"
    source: str = "manual"
    pesticide_task_id: int = 0
    products: list[InspectionReportProductCreate] = []


class InspectionReportUpdate(BaseModel):
    name: str | None = None
    test_date: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    supplier_id: int | None = None
    submit_org: str | None = None
    test_org: str | None = None
    file_url: str | None = None
    status: str | None = None
    products: list[InspectionReportProductCreate] | None = None


class InspectionReportResponse(BaseModel):
    id: int
    report_no: str
    name: str
    file_url: str
    test_date: str
    valid_from: str
    valid_until: str
    supplier_id: int
    supplier_name: str = ""
    submit_org: str
    test_org: str
    status: str
    source: str
    pesticide_task_id: int
    uploaded_by: int
    uploader_name: str = ""
    product_count: int = 0
    products: list[InspectionReportProductResponse] = []
    created_at: str
    updated_at: str


class InspectionReportDetailResponse(BaseModel):
    success: bool = True
    item: InspectionReportResponse
