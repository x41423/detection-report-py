"""Repository helpers for Product, Category, and SKU management."""

from __future__ import annotations

from datetime import datetime
from datetime import date
from typing import Any

from app.db.store import get_connection, query, query_one, run


class ProductRepository:
    """Persist and query product records, categories, and SKUs."""

    # ------------------------------------------------------------------
    # Product CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_product_code(cursor: Any) -> str:
        """Generate product code: SPU-YYYYMMDD-NNN."""
        today = date.today().strftime("%Y%m%d")
        cursor.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(code, -3) AS SIGNED)), 0) + 1 AS seq "
            "FROM Product WHERE code LIKE ?",
            (f"SPU-{today}-%",),
        )
        row = cursor.fetchone()
        seq = int(row["seq"]) if row else 1
        return f"SPU-{today}-{seq:03d}"

    @staticmethod
    def list_products(
        *,
        search: str = "",
        category_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> dict[str, Any]:
        clauses: list[str] = []
        params: list[Any] = []

        if not include_inactive:
            clauses.append("p.is_active = 1")

        if search:
            clauses.append("(p.name LIKE ? OR p.code LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if category_id is not None:
            clauses.append("p.category_id = ?")
            params.append(category_id)

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        rows = query(
            f"""SELECT p.*, c.name AS category_name
                FROM Product p
                LEFT JOIN Category c ON p.category_id = c.id
                {where}
                ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        )
        row = query_one(
            f"SELECT COUNT(*) AS cnt FROM Product p {where}",
            tuple(params),
        )
        total = row["cnt"] if row else 0
        return {"items": rows, "total": total}

    @staticmethod
    def get_product(product_id: int) -> dict[str, Any] | None:
        product = query_one(
            """SELECT p.*, c.name AS category_name
               FROM Product p
               LEFT JOIN Category c ON p.category_id = c.id
               WHERE p.id = ?""",
            (product_id,),
        )
        if product is None:
            return None
        product["skus"] = ProductRepository.list_skus(product_id)
        return product

    @staticmethod
    def create_product(data: dict[str, Any]) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        code = data.get("code", "")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            if not code:
                code = ProductRepository._generate_product_code(cursor)
            cursor.execute(
                """INSERT INTO Product
                   (code, name, alias, category_id, product_type, custom_code,
                    delivery_method, purchase_type, base_unit, image_url,
                    shelf_life_days, purchase_mode, default_supplier_id,
                    description, tax_category_code, tax_rate,
                    custom_field_1, custom_field_2, custom_field_3,
                    has_inspection_report,
                    performance_method, suggested_min_cost, product_tags, fixed_url, notes,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?,
                           ?, ?, ?, ?,
                           ?, ?)""",
                (
                    code,
                    data["name"],
                    data.get("alias", ""),
                    data.get("category_id"),
                    data.get("product_type", "通用"),
                    data.get("custom_code", ""),
                    data.get("delivery_method", "按订单投框"),
                    data.get("purchase_type", "临采"),
                    data.get("base_unit", "斤"),
                    data.get("image_url", ""),
                    data.get("shelf_life_days", 0),
                    data.get("purchase_mode", "订单采购"),
                    data.get("default_supplier_id"),
                    data.get("description", ""),
                    data.get("tax_category_code", ""),
                    data.get("tax_rate", 0),
                    data.get("custom_field_1", ""),
                    data.get("custom_field_2", ""),
                    data.get("custom_field_3", ""),
                    1 if data.get("has_inspection_report") else 0,
                    data.get("performance_method", "计重"),
                    data.get("suggested_min_cost", 0),
                    data.get("product_tags", ""),
                    data.get("fixed_url", ""),
                    data.get("notes", ""),
                    now,
                    now,
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
    def update_product(product_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            fields = [
                "name", "alias", "category_id", "product_type", "custom_code",
                "delivery_method", "purchase_type", "base_unit", "image_url",
                "shelf_life_days", "purchase_mode", "default_supplier_id",
                "description", "tax_category_code", "tax_rate",
                "custom_field_1", "custom_field_2", "custom_field_3",
                "has_inspection_report",
                "performance_method", "suggested_min_cost", "product_tags", "fixed_url", "notes",
            ]
            sets: list[str] = []
            vals: list[Any] = []
            for field in fields:
                if field in data and data[field] is not None:
                    sets.append(f"{field} = ?")
                    val = data[field]
                    if field == "has_inspection_report":
                        val = 1 if val else 0
                    vals.append(val)
            if not sets:
                return True
            cursor.execute(
                f"UPDATE Product SET {', '.join(sets)}, updated_at = ? WHERE id = ?",
                vals + [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product_id],
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def delete_product(product_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE Product SET is_active = 0, updated_at = ? WHERE id = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def activate_product(product_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE Product SET is_active = 1, updated_at = ? WHERE id = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), product_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # Category
    # ------------------------------------------------------------------

    @staticmethod
    def list_categories() -> list[dict[str, Any]]:
        return query(
            "SELECT * FROM Category WHERE is_active = 1 ORDER BY level, sort_order, id",
        )

    # ------------------------------------------------------------------
    # SKU CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def list_skus(product_id: int) -> list[dict[str, Any]]:
        return query(
            "SELECT * FROM ProductSku WHERE product_id = ? ORDER BY id",
            (product_id,),
        )

    @staticmethod
    def create_sku(product_id: int, data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO ProductSku
                   (product_id, sku_code, spec_name, sku_type, is_listed, price, stock,
                    pricing_method, min_order_qty, sale_spec_value, sale_spec_unit,
                    reference_cost, purchase_spec, stock_setting, stock_limit_value,
                    pricing_rule, is_spot, default_stock_slot, waste_ratio, box_type,
                    order_round_up, is_cycle_item)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    product_id,
                    data.get("sku_code", ""),
                    data.get("spec_name", ""),
                    data.get("sku_type", "销售规格"),
                    1 if data.get("is_listed") else 0,
                    data.get("price", 0),
                    data.get("stock", 0),
                    data.get("pricing_method", "manual"),
                    data.get("min_order_qty", 1),
                    data.get("sale_spec_value", 1),
                    data.get("sale_spec_unit", ""),
                    data.get("reference_cost", 0),
                    data.get("purchase_spec", ""),
                    data.get("stock_setting", "none"),
                    data.get("stock_limit_value", 0),
                    data.get("pricing_rule", "normal"),
                    1 if data.get("is_spot") else 0,
                    data.get("default_stock_slot", ""),
                    data.get("waste_ratio", 0),
                    data.get("box_type", "loose"),
                    1 if data.get("order_round_up") else 0,
                    1 if data.get("is_cycle_item") else 0,
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
    def update_sku(sku_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            fields = ["sku_code", "spec_name", "sku_type", "is_listed", "price", "stock",
                       "pricing_method", "min_order_qty", "sale_spec_value",
                       "sale_spec_unit", "reference_cost", "purchase_spec",
                       "stock_setting", "stock_limit_value",
                       "pricing_rule", "is_spot", "default_stock_slot",
                       "waste_ratio", "box_type",
                       "order_round_up", "is_cycle_item"]
            sets: list[str] = []
            vals: list[Any] = []
            for field in fields:
                if field in data and data[field] is not None:
                    sets.append(f"{field} = ?")
                    val = data[field]
                    if field == "is_listed":
                        val = 1 if val else 0
                    vals.append(val)
            if not sets:
                return True
            vals.append(sku_id)
            cursor.execute(
                f"UPDATE ProductSku SET {', '.join(sets)} WHERE id = ?",
                vals,
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # Category management (P1.2)
    # ------------------------------------------------------------------

    @staticmethod
    def create_category(data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            parent_id = data.get("parent_id", 0)
            level = 1
            if parent_id > 0:
                row = query_one("SELECT level FROM Category WHERE id = ?", (parent_id,))
                if row:
                    level = int(row["level"]) + 1
            cursor.execute(
                "INSERT INTO Category (name, parent_id, level, sort_order) VALUES (?, ?, ?, ?)",
                (data.get("name", ""), parent_id, level, data.get("sort_order", 0)),
            )
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def update_category(cat_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            sets: list[str] = []
            values: list[Any] = []
            for field in ("name", "parent_id", "sort_order", "is_active"):
                if field in data and data[field] is not None:
                    sets.append(f"{field} = ?")
                    values.append(data[field])
            if "parent_id" in data:
                parent_id = data["parent_id"]
                level = 1
                if parent_id > 0:
                    row = query_one("SELECT level FROM Category WHERE id = ?", (parent_id,))
                    if row:
                        level = int(row["level"]) + 1
                sets.append("level = ?")
                values.append(level)
            if not sets:
                return False
            values.append(cat_id)
            cursor.execute(f"UPDATE Category SET {', '.join(sets)} WHERE id = ?", values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def delete_category(cat_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Category SET is_active = 0 WHERE id = ?", (cat_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
