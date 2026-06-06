"""Pydantic models for Order management (订单管理)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Order Item
# ---------------------------------------------------------------------------


class OrderItemCreate(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    product_id: str | None = None
    category: str | None = None
    unit: str = Field(default="斤")
    quantity: float = Field(default=0, ge=0)
    unit_price: float = Field(default=0, ge=0)


class OrderItemResponse(BaseModel):
    id: int
    product_name: str
    product_id: str | None
    category: str | None
    unit: str
    quantity: float
    unit_price: float
    amount: float


# ---------------------------------------------------------------------------
# Order Record
# ---------------------------------------------------------------------------


class OrderCreate(BaseModel):
    """新建订单 — 对齐观麦订单创建页面结构。"""
    # -- 客户信息 --
    merchant_name: str | None = None
    merchant_id: str | None = None
    merchant_tag: str | None = Field(default=None, description="商户标签")
    # -- 时间 --
    order_date: str = Field(..., description="YYYY-MM-DD")
    receive_start_date: str | None = Field(default=None, description="收货开始日期 YYYY-MM-DD")
    receive_end_date: str | None = Field(default=None, description="收货结束日期 YYYY-MM-DD")
    receive_start_time: str | None = Field(default=None, description="收货开始时间 HH:mm")
    receive_end_time: str | None = Field(default=None, description="收货结束时间 HH:mm")
    operation_time: str | None = Field(default=None, description="运营时间选择")
    # -- 配送 --
    delivery_method: str | None = None
    receiver: str | None = Field(default=None, description="收货人")
    delivery_address: str | None = Field(default=None, description="收货地址")
    sign_method: str | None = Field(default=None, description="签收方式")
    # -- 订单信息 --
    order_type: str | None = None
    freight: float = Field(default=0, ge=0)
    discount_amount: float = Field(default=0, ge=0)
    remark: str | None = Field(default=None, max_length=128, description="订单备注 128字以内")
    # -- 关联 --
    related_outbound_no: str | None = Field(default=None, description="关联出库单号")
    third_party_order_no: str | None = Field(default=None, description="第三方订单号")
    # -- 商户自定义 --
    custom_field_1: str | None = None
    custom_field_2: str | None = None
    custom_field_3: str | None = None
    # -- 商品 --
    items: list[OrderItemCreate] = Field(default_factory=list)


class OrderUpdate(BaseModel):
    merchant_name: str | None = None
    merchant_tag: str | None = None
    order_date: str | None = None
    receive_start_date: str | None = None
    receive_end_date: str | None = None
    receive_start_time: str | None = None
    receive_end_time: str | None = None
    operation_time: str | None = None
    delivery_method: str | None = None
    receiver: str | None = None
    delivery_address: str | None = None
    sign_method: str | None = None
    order_type: str | None = None
    freight: float | None = None
    discount_amount: float | None = None
    remark: str | None = None
    related_outbound_no: str | None = None
    third_party_order_no: str | None = None
    custom_field_1: str | None = None
    custom_field_2: str | None = None
    custom_field_3: str | None = None


class OrderResponse(BaseModel):
    id: int
    order_no: str
    merchant_name: str | None
    merchant_id: str | None
    merchant_tag: str | None = None
    order_date: str
    receive_start_date: str | None
    receive_end_date: str | None
    receive_start_time: str | None
    receive_end_time: str | None
    operation_time: str | None
    delivery_method: str | None
    receiver: str | None
    delivery_address: str | None
    sign_method: str | None
    order_type: str | None
    order_amount: float
    freight: float
    sales_amount_incl_freight: float
    discount_amount: float
    order_status: str
    outbound_status: str | None
    # -- v5 新增字段 --
    payment_status: str | None = None
    loading_status: str | None = None
    print_status: str | None = None
    driver_name: str | None = None
    order_source: str | None = None
    sorting_status: str | None = None
    inspection_status: str | None = None
    cabinet_status: str | None = None
    route_name: str | None = None
    pickup_point: str | None = None
    total_order_quantity: float = 0
    accounting_quantity_sale: float = 0
    accounting_quantity_base: float = 0
    product_category_count: int = 0
    merchant_custom_code: str | None = None
    after_sale_amount: float = 0
    should_refund_amount: float = 0
    edit_status: str | None = None
    vehicle_status: str | None = None
    batch_status: str | None = None
    batch_merchant_name: str | None = None
    main_sorting_category: str | None = None
    main_sorting_category_count: int = 0
    remark: str | None
    related_outbound_no: str | None
    third_party_order_no: str | None
    custom_field_1: str | None
    custom_field_2: str | None
    custom_field_3: str | None
    operator: str | None
    items: list[OrderItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# After-Sale
# ---------------------------------------------------------------------------


class OrderAfterSaleCreate(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    product_id: str | None = None
    after_sale_type: str | None = None
    return_quantity: float = Field(default=0, ge=0)
    return_amount: float = Field(default=0, ge=0)
    accounting_quantity: float = Field(default=0, ge=0)


class OrderAfterSaleResponse(BaseModel):
    id: int
    order_id: int
    product_name: str
    after_sale_type: str | None
    return_quantity: float
    return_amount: float
    accounting_quantity: float
    total_abnormal: float
    total_return: float
    status: str


# ---------------------------------------------------------------------------
# Copy Order Options
# ---------------------------------------------------------------------------


class OrderCopyOptions(BaseModel):
    """复制订单选项 — 对齐观麦复制订单弹窗。"""
    copy_type: str = Field(default="normal", description="复制类型: normal=常规, yes=复制到订单, no=复制到补单")
    sync_unit_price: str = Field(default="yes", description="是否同步商品单价: yes/no")
    sync_price_change_rate: str = Field(default="yes", description="是否同步单价变化率: yes/no")
    copy_outbound_quantity: str = Field(default="no", description="是否复制出库数: yes/no")


# ---------------------------------------------------------------------------
# Column Preference
# ---------------------------------------------------------------------------


class ColumnPreferenceRequest(BaseModel):
    """保存用户列偏好。"""
    page_key: str = Field(..., description="页面标识，如 'order_list'")
    visible_columns: list[str] = Field(default_factory=list, description="可见列的 key 列表")


class ColumnPreferenceResponse(BaseModel):
    """用户列偏好响应。"""
    page_key: str
    visible_columns: list[str] = Field(default_factory=list)
