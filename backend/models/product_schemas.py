"""Pydantic models for Product management (商品库)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


class ProductCreate(BaseModel):
    """新建商品 — 对齐观麦商品创建页面结构。"""

    name: str = Field(..., min_length=1, max_length=200)
    alias: str = Field(default="")
    category_id: int | None = None
    product_type: str = Field(default="通用")
    custom_code: str = Field(default="")
    delivery_method: str = Field(default="按订单投框")
    purchase_type: str = Field(default="临采")
    base_unit: str = Field(default="斤")
    image_url: str = Field(default="")
    shelf_life_days: int = Field(default=0)
    purchase_mode: str = Field(default="订单采购")
    default_supplier_id: int | None = None
    description: str = Field(default="")
    tax_category_code: str = Field(default="")
    tax_rate: float = Field(default=0, ge=0)
    custom_field_1: str = Field(default="")
    custom_field_2: str = Field(default="")
    custom_field_3: str = Field(default="")
    has_inspection_report: bool = Field(default=False)
    # Phase 3 字段
    performance_method: str = Field(default="计重")
    suggested_min_cost: float = Field(default=0, ge=0)
    product_tags: str = Field(default="")
    fixed_url: str = Field(default="")
    notes: str = Field(default="")


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    alias: str | None = None
    category_id: int | None = None
    product_type: str | None = None
    custom_code: str | None = None
    delivery_method: str | None = None
    purchase_type: str | None = None
    base_unit: str | None = None
    image_url: str | None = None
    shelf_life_days: int | None = None
    purchase_mode: str | None = None
    default_supplier_id: int | None = None
    description: str | None = None
    tax_category_code: str | None = None
    tax_rate: float | None = None
    custom_field_1: str | None = None
    custom_field_2: str | None = None
    custom_field_3: str | None = None
    has_inspection_report: bool | None = None
    # Phase 3 字段
    performance_method: str | None = None
    suggested_min_cost: float | None = None
    product_tags: str | None = None
    fixed_url: str | None = None
    notes: str | None = None


class ProductSkuResponse(BaseModel):
    id: int
    product_id: int
    sku_code: str
    spec_name: str
    sku_type: str
    is_listed: int
    price: float
    stock: float
    # Phase 1 字段
    pricing_method: str = "manual"
    min_order_qty: float = 1
    sale_spec_value: float = 1
    sale_spec_unit: str = ""
    reference_cost: float = 0
    purchase_spec: str = ""
    stock_setting: str = "none"
    stock_limit_value: float = 0
    # Phase 2 字段
    pricing_rule: str = "normal"
    is_spot: int = 0
    default_stock_slot: str = ""
    waste_ratio: float = 0
    box_type: str = "loose"
    # Phase 3 字段
    order_round_up: int = 0
    is_cycle_item: int = 0


class ProductResponse(BaseModel):
    id: int
    code: str
    name: str
    alias: str
    category_id: int | None
    category_name: str | None
    product_type: str
    custom_code: str
    delivery_method: str
    purchase_type: str
    base_unit: str
    image_url: str
    shelf_life_days: int
    purchase_mode: str
    default_supplier_id: int | None
    description: str
    tax_category_code: str
    tax_rate: float
    custom_field_1: str
    custom_field_2: str
    custom_field_3: str
    has_inspection_report: int
    is_active: int
    # Phase 3 字段
    performance_method: str = "计重"
    suggested_min_cost: float = 0
    product_tags: str = ""
    fixed_url: str = ""
    notes: str = ""
    skus: list[ProductSkuResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Product SKU
# ---------------------------------------------------------------------------


class ProductSkuCreate(BaseModel):
    sku_code: str = Field(default="")
    spec_name: str = Field(default="")
    sku_type: str = Field(default="销售规格")
    is_listed: bool = Field(default=True)
    price: float = Field(default=0, ge=0)
    stock: float = Field(default=0, ge=0)
    # Phase 1 字段
    pricing_method: str = Field(default="manual")
    min_order_qty: float = Field(default=1, ge=1)
    sale_spec_value: float = Field(default=1, ge=0)
    sale_spec_unit: str = Field(default="")
    reference_cost: float = Field(default=0, ge=0)
    purchase_spec: str = Field(default="")
    stock_setting: str = Field(default="none")
    stock_limit_value: float = Field(default=0, ge=0)
    # Phase 2 字段
    pricing_rule: str = Field(default="normal")
    is_spot: bool = Field(default=False)
    default_stock_slot: str = Field(default="")
    waste_ratio: float = Field(default=0, ge=0)
    box_type: str = Field(default="loose")
    # Phase 3 字段
    order_round_up: bool = Field(default=False)
    is_cycle_item: bool = Field(default=False)
