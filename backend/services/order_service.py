"""Business logic for Order management with inventory sync."""
from __future__ import annotations

from datetime import date
from typing import Any

from app.db.order_repository import OrderRepository
from app.db.inventory_repository import InventoryRepository
from backend.api.response_utils import list_response, mutation_response
from backend.models.order_schemas import (
    OrderCreate,
    OrderUpdate,
    OrderAfterSaleCreate,
)


class OrderService:
    """Coordinate order CRUD, status transitions, and outbound inventory sync."""

    def __init__(self) -> None:
        pass

    # ==================================================================
    # Order
    # ==================================================================

    def create_order(self, data: OrderCreate) -> dict[str, Any]:
        rid = OrderRepository.create_order(data.model_dump())
        record = OrderRepository.get_order_by_id(rid)
        items = OrderRepository.get_order_items(rid)
        return mutation_response(
            "订单已创建",
            record=self._serialize_order(record, items),
        )

    def list_orders(
        self, *, search="", merchant_name=None, order_status=None,
        date_mode=None, date_from=None, date_to=None,
        limit=20, offset=0,
    ) -> dict[str, Any]:
        rows = OrderRepository.list_orders(
            search=search, merchant_name=merchant_name, order_status=order_status,
            date_mode=date_mode, date_from=date_from, date_to=date_to,
            limit=limit, offset=offset,
        )
        total = OrderRepository.count_orders(
            search=search, merchant_name=merchant_name, order_status=order_status,
            date_mode=date_mode, date_from=date_from, date_to=date_to,
        )
        items = [self._serialize_order_summary(r) for r in rows]
        return list_response(items, total, f"已加载 {len(items)} 条订单")

    def get_order(self, order_id: int) -> dict[str, Any]:
        record = OrderRepository.get_order_by_id(order_id)
        if record is None:
            raise LookupError(f"订单 {order_id} 不存在")
        items = OrderRepository.get_order_items(order_id)
        return self._serialize_order(record, items)

    def update_order(self, order_id: int, data: OrderUpdate) -> dict[str, Any]:
        record = OrderRepository.get_order_by_id(order_id)
        if record is None:
            raise LookupError(f"订单 {order_id} 不存在")
        if record["order_status"] == "delivered":
            raise ValueError("已发货订单不可修改")
        payload = data.model_dump(exclude_none=True)
        OrderRepository.update_order(order_id, payload)
        return self.get_order(order_id)

    def confirm_outbound(self, order_id: int) -> dict[str, Any]:
        """确认出库 → 自动同步库存 (OUT)"""
        record = OrderRepository.get_order_by_id(order_id)
        if record is None:
            raise LookupError(f"订单 {order_id} 不存在")
        if record["order_status"] == "delivered":
            raise ValueError("订单已出库，无需重复操作")

        items = OrderRepository.get_order_items(order_id)
        today = date.today().isoformat()

        for item in items:
            self._write_outbound_txn(item=item, business_date=record["order_date"] or today,
                                     order_no=record["order_no"])

        OrderRepository.update_order_status(order_id, "delivered")
        from app.db.store import get_connection
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute(
                "UPDATE OrderRecord SET outbound_status = 'completed', "
                "last_operate_time = ? WHERE id = ?",
                (today, order_id),
            )
            conn.commit()
        finally:
            c.close()
        return mutation_response("订单已出库，库存已同步")

    # ==================================================================
    # After-Sale
    # ==================================================================

    def create_after_sale(self, order_id: int, data: OrderAfterSaleCreate) -> dict[str, Any]:
        record = OrderRepository.get_order_by_id(order_id)
        if record is None:
            raise LookupError(f"订单 {order_id} 不存在")
        as_id = OrderRepository.create_after_sale(order_id, data.model_dump())
        return mutation_response(
            "售后记录已创建",
            after_sale_id=as_id,
        )

    def get_after_sales(self, order_id: int) -> list[dict[str, Any]]:
        return OrderRepository.get_after_sales(order_id)

    # ==================================================================
    # Delete Order
    # ==================================================================

    def delete_order(self, order_id: int) -> dict[str, Any]:
        OrderRepository.delete_order(order_id)
        return mutation_response("订单已删除")

    # ==================================================================
    # Copy Order
    # ==================================================================

    def copy_order(self, order_id: int, options: dict[str, Any], operator: str | None = None) -> dict[str, Any]:
        new_id = OrderRepository.copy_order(order_id, options, operator)
        new_order = OrderRepository.get_order_by_id(new_id)
        return mutation_response(
            "订单已复制",
            new_order_id=new_id,
            new_order_no=new_order["order_no"] if new_order else "",
        )

    # ==================================================================
    # Column Preference
    # ==================================================================

    def save_column_preference(self, user_id: int, page_key: str, columns: list[str]) -> dict[str, Any]:
        OrderRepository.save_column_preference(user_id, page_key, columns)
        return mutation_response("列偏好已保存")

    def get_column_preference(self, user_id: int, page_key: str) -> dict[str, Any]:
        columns = OrderRepository.get_column_preference(user_id, page_key)
        return {"success": True, "visible_columns": columns or []}

    # ==================================================================
    # Internals
    # ==================================================================

    def _write_outbound_txn(self, *, item: dict, business_date: str, order_no: str) -> None:
        from app.db.store import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            unit_id = InventoryRepository._get_or_create_unit_id(
                cursor, item.get("unit", "斤")
            )
            cursor.execute(
                """INSERT INTO InventoryTransaction
                   (veg_id, display_name, normalized_name, unit_id, direction,
                    quantity_delta, business_date, source_type, source_ref_id, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    None,
                    item["product_name"],
                    item["product_name"],
                    unit_id,
                    "OUT",
                    float(item.get("quantity", 0)),
                    business_date,
                    "purchase_outbound",
                    item["id"],
                    f"订单出库 {order_no}",
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ==================================================================
    # Serialization
    # ==================================================================

    @staticmethod
    def _serialize_order(record: dict, items: list[dict]) -> dict:
        return {
            "id": record["id"],
            "order_no": record["order_no"],
            "merchant_name": record.get("merchant_name"),
            "merchant_id": record.get("merchant_id"),
            "merchant_tag": record.get("merchant_tag"),
            "order_date": record["order_date"],
            "receive_start_date": record.get("receive_start_date"),
            "receive_end_date": record.get("receive_end_date"),
            "receive_start_time": record.get("receive_start_time"),
            "receive_end_time": record.get("receive_end_time"),
            "operation_time": record.get("operation_time"),
            "delivery_method": record.get("delivery_method"),
            "receiver": record.get("receiver"),
            "delivery_address": record.get("delivery_address"),
            "sign_method": record.get("sign_method"),
            "order_type": record.get("order_type"),
            "order_amount": record.get("order_amount", 0),
            "freight": record.get("freight", 0),
            "sales_amount_incl_freight": record.get("sales_amount_incl_freight", 0),
            "discount_amount": record.get("discount_amount", 0),
            "order_status": record.get("order_status"),
            "outbound_status": record.get("outbound_status"),
            "remark": record.get("remark"),
            "related_outbound_no": record.get("related_outbound_no"),
            "third_party_order_no": record.get("third_party_order_no"),
            "custom_field_1": record.get("custom_field_1"),
            "custom_field_2": record.get("custom_field_2"),
            "custom_field_3": record.get("custom_field_3"),
            "operator": record.get("operator"),
            # -- v5 新增字段 --
            "payment_status": record.get("payment_status"),
            "loading_status": record.get("loading_status"),
            "print_status": record.get("print_status"),
            "driver_name": record.get("driver_name"),
            "order_source": record.get("order_source"),
            "sorting_status": record.get("sorting_status"),
            "inspection_status": record.get("inspection_status"),
            "cabinet_status": record.get("cabinet_status"),
            "route_name": record.get("route_name"),
            "pickup_point": record.get("pickup_point"),
            "total_order_quantity": record.get("total_order_quantity", 0),
            "accounting_quantity_sale": record.get("accounting_quantity_sale", 0),
            "accounting_quantity_base": record.get("accounting_quantity_base", 0),
            "product_category_count": record.get("product_category_count", 0),
            "merchant_custom_code": record.get("merchant_custom_code"),
            "after_sale_amount": record.get("after_sale_amount", 0),
            "should_refund_amount": record.get("should_refund_amount", 0),
            "edit_status": record.get("edit_status"),
            "vehicle_status": record.get("vehicle_status"),
            "batch_status": record.get("batch_status"),
            "batch_merchant_name": record.get("batch_merchant_name"),
            "main_sorting_category": record.get("main_sorting_category"),
            "main_sorting_category_count": record.get("main_sorting_category_count", 0),
            "items": [
                {
                    "id": it["id"],
                    "product_name": it["product_name"],
                    "product_id": it.get("product_id"),
                    "category": it.get("category"),
                    "unit": it.get("unit"),
                    "quantity": it["quantity"],
                    "unit_price": it["unit_price"],
                    "amount": it["amount"],
                }
                for it in items
            ],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }

    @staticmethod
    def _serialize_order_summary(record: dict) -> dict:
        return {
            "id": record["id"],
            "order_no": record["order_no"],
            "merchant_name": record.get("merchant_name"),
            "merchant_tag": record.get("merchant_tag"),
            "order_date": record["order_date"],
            "order_amount": record.get("order_amount", 0),
            "order_status": record.get("order_status"),
            "outbound_status": record.get("outbound_status"),
            "remark": record.get("remark"),
            "created_at": record["created_at"],
        }
