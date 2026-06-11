"""Repository helpers for Purchase In / Return operations."""
from __future__ import annotations

from datetime import date
from typing import Any

from app.db.store import get_connection, query, query_one


class PurchaseRepository:
    """Persist and query purchase-in and purchase-return records."""

    # ------------------------------------------------------------------
    # Code generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_in_code(cursor: Any) -> str:
        today = date.today().strftime("%Y%m%d")
        cursor.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(order_no, -3) AS INTEGER)), 0) + 1 AS seq "
            "FROM PurchaseInRecord WHERE order_no LIKE ?",
            (f"PIN-{today}-%",),
        )
        row = cursor.fetchone()
        seq = int(row["seq"]) if row else 1
        return f"PIN-{today}-{seq:03d}"

    @staticmethod
    def _generate_return_code(cursor: Any) -> str:
        today = date.today().strftime("%Y%m%d")
        cursor.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(order_no, -3) AS INTEGER)), 0) + 1 AS seq "
            "FROM PurchaseReturnRecord WHERE order_no LIKE ?",
            (f"PRT-{today}-%",),
        )
        row = cursor.fetchone()
        seq = int(row["seq"]) if row else 1
        return f"PRT-{today}-{seq:03d}"

    # ------------------------------------------------------------------
    # Purchase In — CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create_in(data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            code = PurchaseRepository._generate_in_code(cursor)
            cursor.execute(
                """INSERT INTO PurchaseInRecord
                   (order_no, supplier_id, inbound_date, remark)
                   VALUES (?, ?, ?, ?)""",
                (code, data["supplier_id"], data["inbound_date"], data.get("remark")),
            )
            record_id = cursor.lastrowid
            for item in data.get("items", []):
                cursor.execute(
                    """INSERT INTO PurchaseInItem
                       (record_id, veg_name, category, unit, quantity, unit_price, amount, tax_rate)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record_id,
                        item["veg_name"],
                        item.get("category"),
                        item.get("unit", "斤"),
                        item.get("quantity", 0),
                        item.get("unit_price", 0),
                        round(item.get("quantity", 0) * item.get("unit_price", 0), 2),
                        item.get("tax_rate", 0),
                    ),
                )
            conn.commit()
            return record_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def get_in_by_id(record_id: int) -> dict[str, Any] | None:
        return query_one(
            "SELECT * FROM PurchaseInRecord WHERE id = ?", (record_id,)
        )

    @staticmethod
    def get_in_items(record_id: int) -> list[dict[str, Any]]:
        return query(
            "SELECT * FROM PurchaseInItem WHERE record_id = ?", (record_id,)
        )

    @staticmethod
    def list_in(
        *,
        search: str = "",
        supplier_id: int | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("r.order_no LIKE ?")
            params.append(f"%{search}%")
        if supplier_id:
            clauses.append("r.supplier_id = ?")
            params.append(supplier_id)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return query(
            f"SELECT r.*, s.name AS supplier_name "
            f"FROM PurchaseInRecord r JOIN Supplier s ON s.id = r.supplier_id "
            f"{where} ORDER BY r.created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )

    @staticmethod
    def count_in(
        *, search: str = "", supplier_id: int | None = None, status: str | None = None
    ) -> int:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("r.order_no LIKE ?")
            params.append(f"%{search}%")
        if supplier_id:
            clauses.append("r.supplier_id = ?")
            params.append(supplier_id)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = query_one(
            f"SELECT COUNT(*) AS cnt FROM PurchaseInRecord r {where}", tuple(params)
        )
        return row["cnt"] if row else 0

    @staticmethod
    def update_in_status(record_id: int, status: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE PurchaseInRecord SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, record_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # Purchase Return — CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create_return(data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            code = PurchaseRepository._generate_return_code(cursor)
            cursor.execute(
                """INSERT INTO PurchaseReturnRecord
                   (order_no, supplier_id, return_date, remark)
                   VALUES (?, ?, ?, ?)""",
                (code, data["supplier_id"], data["return_date"], data.get("remark")),
            )
            record_id = cursor.lastrowid
            for item in data.get("items", []):
                cursor.execute(
                    """INSERT INTO PurchaseReturnItem
                       (record_id, veg_name, category, unit, quantity, unit_price, amount)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record_id,
                        item["veg_name"],
                        item.get("category"),
                        item.get("unit", "斤"),
                        item.get("quantity", 0),
                        item.get("unit_price", 0),
                        round(item.get("quantity", 0) * item.get("unit_price", 0), 2),
                    ),
                )
            conn.commit()
            return record_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def get_return_by_id(record_id: int) -> dict[str, Any] | None:
        return query_one(
            "SELECT * FROM PurchaseReturnRecord WHERE id = ?", (record_id,)
        )

    @staticmethod
    def get_return_items(record_id: int) -> list[dict[str, Any]]:
        return query(
            "SELECT * FROM PurchaseReturnItem WHERE record_id = ?", (record_id,)
        )

    @staticmethod
    def list_return(
        *, search: str = "", supplier_id: int | None = None, status: str | None = None,
        limit: int = 20, offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("r.order_no LIKE ?")
            params.append(f"%{search}%")
        if supplier_id:
            clauses.append("r.supplier_id = ?")
            params.append(supplier_id)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return query(
            f"SELECT r.*, s.name AS supplier_name "
            f"FROM PurchaseReturnRecord r JOIN Supplier s ON s.id = r.supplier_id "
            f"{where} ORDER BY r.created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )

    @staticmethod
    def count_return(
        *, search: str = "", supplier_id: int | None = None, status: str | None = None
    ) -> int:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("r.order_no LIKE ?")
            params.append(f"%{search}%")
        if supplier_id:
            clauses.append("r.supplier_id = ?")
            params.append(supplier_id)
        if status:
            clauses.append("r.status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = query_one(
            f"SELECT COUNT(*) AS cnt FROM PurchaseReturnRecord r {where}", tuple(params)
        )
        return row["cnt"] if row else 0

    @staticmethod
    def update_return_status(record_id: int, status: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE PurchaseReturnRecord SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, record_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
