"""Repository helpers for Order management."""
from __future__ import annotations

from datetime import date
from typing import Any

from app.db.store import get_connection, query, query_one


class OrderRepository:
    """Persist and query order records, items, and after-sale entries."""

    # ------------------------------------------------------------------
    # Code generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_order_no(cursor: Any) -> str:
        today = date.today().strftime("%Y%m%d")
        cursor.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(order_no, -3) AS INTEGER)), 0) + 1 AS seq "
            "FROM OrderRecord WHERE order_no LIKE ?",
            (f"ORD-{today}-%",),
        )
        row = cursor.fetchone()
        seq = int(row["seq"]) if row else 1
        return f"ORD-{today}-{seq:03d}"

    # ------------------------------------------------------------------
    # Order CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create_order(data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            code = OrderRepository._generate_order_no(cursor)
            cursor.execute(
                """INSERT INTO OrderRecord
                   (order_no, merchant_name, merchant_id, order_date,
                    delivery_method, order_type, freight, discount_amount, remark,
                    receive_start_date, receive_end_date, receive_start_time, receive_end_time,
                    operation_time, receiver, delivery_address, sign_method,
                    related_outbound_no, third_party_order_no,
                    custom_field_1, custom_field_2, custom_field_3)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?,
                           ?, ?, ?, ?,
                           ?, ?,
                           ?, ?, ?)""",
                (
                    code,
                    data.get("merchant_name"),
                    data.get("merchant_id"),
                    data["order_date"],
                    data.get("delivery_method"),
                    data.get("order_type"),
                    data.get("freight", 0),
                    data.get("discount_amount", 0),
                    data.get("remark"),
                    data.get("receive_start_date"),
                    data.get("receive_end_date"),
                    data.get("receive_start_time"),
                    data.get("receive_end_time"),
                    data.get("operation_time"),
                    data.get("receiver"),
                    data.get("delivery_address"),
                    data.get("sign_method"),
                    data.get("related_outbound_no"),
                    data.get("third_party_order_no"),
                    data.get("custom_field_1"),
                    data.get("custom_field_2"),
                    data.get("custom_field_3"),
                ),
            )
            order_id = cursor.lastrowid
            total_amount = 0.0
            for item in data.get("items", []):
                qty = float(item.get("quantity", 0))
                price = float(item.get("unit_price", 0))
                amount = round(qty * price, 2)
                total_amount += amount
                cursor.execute(
                    """INSERT INTO OrderItem
                       (order_id, product_id, product_name, category, unit,
                        quantity, unit_price, amount)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        order_id,
                        item.get("product_id"),
                        item["product_name"],
                        item.get("category"),
                        item.get("unit", "斤"),
                        qty,
                        price,
                        amount,
                    ),
                )
            # update totals
            freight = float(data.get("freight", 0))
            discount = float(data.get("discount_amount", 0))
            sales_incl_freight = round(total_amount + freight - discount, 2)
            cursor.execute(
                """UPDATE OrderRecord
                   SET order_amount = ?, sales_amount_incl_freight = ?
                   WHERE id = ?""",
                (round(total_amount, 2), sales_incl_freight, order_id),
            )
            conn.commit()
            return order_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def get_order_by_id(order_id: int) -> dict[str, Any] | None:
        return query_one("SELECT * FROM OrderRecord WHERE id = ?", (order_id,))

    @staticmethod
    def get_order_items(order_id: int) -> list[dict[str, Any]]:
        return query("SELECT * FROM OrderItem WHERE order_id = ?", (order_id,))

    @staticmethod
    def list_orders(
        *,
        search: str = "",
        merchant_name: str | None = None,
        order_status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("order_no LIKE ?")
            params.append(f"%{search}%")
        if merchant_name:
            clauses.append("merchant_name = ?")
            params.append(merchant_name)
        if order_status:
            clauses.append("order_status = ?")
            params.append(order_status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return query(
            f"SELECT * FROM OrderRecord {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )

    @staticmethod
    def count_orders(
        *, search: str = "", merchant_name: str | None = None, order_status: str | None = None
    ) -> int:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("order_no LIKE ?")
            params.append(f"%{search}%")
        if merchant_name:
            clauses.append("merchant_name = ?")
            params.append(merchant_name)
        if order_status:
            clauses.append("order_status = ?")
            params.append(order_status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = query_one(f"SELECT COUNT(*) AS cnt FROM OrderRecord {where}", tuple(params))
        return row["cnt"] if row else 0

    @staticmethod
    def update_order(order_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            sets = []
            vals: list[Any] = []
            for field in ("merchant_name", "order_date", "delivery_method",
                           "order_type", "freight", "discount_amount", "remark",
                           "receive_start_date", "receive_end_date", "receive_start_time", "receive_end_time",
                           "operation_time", "receiver", "delivery_address", "sign_method",
                           "related_outbound_no", "third_party_order_no",
                           "custom_field_1", "custom_field_2", "custom_field_3"):
                if field in data and data[field] is not None:
                    sets.append(f"{field} = ?")
                    vals.append(data[field])
            if not sets:
                return True
            vals.append(order_id)
            cursor.execute(
                f"UPDATE OrderRecord SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                vals,
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def update_order_status(order_id: int, status: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE OrderRecord SET order_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, order_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # After-Sale
    # ------------------------------------------------------------------

    @staticmethod
    def create_after_sale(order_id: int, data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO OrderAfterSale
                   (order_id, product_id, product_name, after_sale_type,
                    return_quantity, return_amount, accounting_quantity)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    order_id,
                    data.get("product_id"),
                    data["product_name"],
                    data.get("after_sale_type"),
                    data.get("return_quantity", 0),
                    data.get("return_amount", 0),
                    data.get("accounting_quantity", 0),
                ),
            )
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def get_after_sales(order_id: int) -> list[dict[str, Any]]:
        return query("SELECT * FROM OrderAfterSale WHERE order_id = ?", (order_id,))

    # ------------------------------------------------------------------
    # Delete Order
    # ------------------------------------------------------------------

    @staticmethod
    def delete_order(order_id: int) -> bool:
        """Delete an order. Returns False if order is delivered (cannot delete)."""
        order = query_one("SELECT order_status FROM OrderRecord WHERE id = ?", (order_id,))
        if order is None:
            raise LookupError(f"订单 {order_id} 不存在")
        if order["order_status"] == "delivered":
            raise ValueError("已出库订单不能删除，请先撤销出库")
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM OrderItem WHERE order_id = ?", (order_id,))
            cursor.execute("DELETE FROM OrderAfterSale WHERE order_id = ?", (order_id,))
            cursor.execute("DELETE FROM OrderRecord WHERE id = ?", (order_id,))
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # Copy Order
    # ------------------------------------------------------------------

    @staticmethod
    def copy_order(order_id: int, options: dict[str, Any], operator: str | None = None) -> int:
        """Copy an order with options. Returns new order_id."""
        original = query_one("SELECT * FROM OrderRecord WHERE id = ?", (order_id,))
        if original is None:
            raise LookupError(f"订单 {order_id} 不存在")
        items = query("SELECT * FROM OrderItem WHERE order_id = ?", (order_id,))
        conn = get_connection()
        cursor = conn.cursor()
        try:
            new_code = OrderRepository._generate_order_no(cursor)
            copy_type = options.get("copy_type", "normal")
            sync_price = options.get("sync_unit_price", "yes") == "yes"
            sync_rate = options.get("sync_price_change_rate", "yes") == "yes"
            copy_outbound = options.get("copy_outbound_quantity", "no") == "yes"

            new_order_type = original["order_type"] or ""
            if copy_type == "no":
                new_order_type = "supplement"

            cursor.execute(
                """INSERT INTO OrderRecord
                   (order_no, merchant_name, merchant_id, merchant_tag, order_date,
                    delivery_method, order_type, freight, discount_amount, remark,
                    receive_start_date, receive_end_date, receive_start_time, receive_end_time,
                    operation_time, receiver, delivery_address, sign_method,
                    related_outbound_no, third_party_order_no,
                    custom_field_1, custom_field_2, custom_field_3, operator)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    new_code,
                    original["merchant_name"],
                    original["merchant_id"],
                    original.get("merchant_tag"),
                    original["order_date"],
                    original["delivery_method"],
                    new_order_type,
                    original.get("freight", 0),
                    original.get("discount_amount", 0),
                    original.get("remark"),
                    original.get("receive_start_date"),
                    original.get("receive_end_date"),
                    original.get("receive_start_time"),
                    original.get("receive_end_time"),
                    original.get("operation_time"),
                    original.get("receiver"),
                    original.get("delivery_address"),
                    original.get("sign_method"),
                    original.get("related_outbound_no"),
                    original.get("third_party_order_no"),
                    original.get("custom_field_1"),
                    original.get("custom_field_2"),
                    original.get("custom_field_3"),
                    operator,
                ),
            )
            new_order_id = cursor.lastrowid
            total_amount = 0.0
            for item in items:
                qty = float(item.get("quantity", 0))
                price = float(item.get("unit_price", 0))
                if not sync_price:
                    price = 0
                if sync_rate and sync_price:
                    pass  # keep original price
                amount = round(qty * price, 2)
                total_amount += amount
                cursor.execute(
                    """INSERT INTO OrderItem
                       (order_id, product_id, product_name, category, unit,
                        quantity, unit_price, amount)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        new_order_id,
                        item.get("product_id"),
                        item["product_name"],
                        item.get("category"),
                        item.get("unit", "斤"),
                        qty,
                        price,
                        amount,
                    ),
                )
            freight = float(original.get("freight", 0))
            discount = float(original.get("discount_amount", 0))
            sales_incl_freight = round(total_amount + freight - discount, 2)
            new_status = "sorting" if copy_outbound else "pending"
            cursor.execute(
                """UPDATE OrderRecord
                   SET order_amount = ?, sales_amount_incl_freight = ?, order_status = ?
                   WHERE id = ?""",
                (round(total_amount, 2), sales_incl_freight, new_status, new_order_id),
            )
            conn.commit()
            return new_order_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # Column Preference
    # ------------------------------------------------------------------

    @staticmethod
    def save_column_preference(user_id: int, page_key: str, columns: list[str]) -> None:
        import json
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO UserColumnPreference (user_id, page_key, visible_columns, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(user_id, page_key) DO UPDATE SET
                       visible_columns = excluded.visible_columns,
                       updated_at = CURRENT_TIMESTAMP""",
                (user_id, page_key, json.dumps(columns)),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def get_column_preference(user_id: int, page_key: str) -> list[str] | None:
        import json
        row = query_one(
            "SELECT visible_columns FROM UserColumnPreference WHERE user_id = ? AND page_key = ?",
            (user_id, page_key),
        )
        if row is None:
            return None
        return json.loads(row["visible_columns"])
