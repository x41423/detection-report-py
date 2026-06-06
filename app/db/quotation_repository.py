"""Repository helpers for Quotation management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db.store import get_connection, query, query_one


class QuotationRepository:
    """Persist and query quotation records and their product associations."""

    # ------------------------------------------------------------------
    # Quotation CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def list_quotations(
        *,
        search: str = "",
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        clauses = ["1=1"]
        params: list[Any] = []

        if search:
            clauses.append("(q.name LIKE ? OR q.code LIKE ? OR q.external_name LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if status:
            clauses.append("q.status = ?")
            params.append(status)

        where = " AND ".join(clauses)

        rows = query(
            f"""SELECT q.*,
                       (SELECT COUNT(*) FROM QuotationProduct qp WHERE qp.quotation_id = q.id AND qp.is_active = 1) AS product_count
                FROM Quotation q
                WHERE {where}
                ORDER BY q.created_at DESC
                LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        )
        row = query_one(
            f"SELECT COUNT(*) AS cnt FROM Quotation q WHERE {where}",
            tuple(params),
        )
        total = row["cnt"] if row else 0
        return {"items": rows, "total": total}

    @staticmethod
    def get_quotation(quotation_id: int) -> dict[str, Any] | None:
        q = query_one(
            """SELECT q.*,
                       (SELECT COUNT(*) FROM QuotationProduct qp WHERE qp.quotation_id = q.id AND qp.is_active = 1) AS product_count
                FROM Quotation q WHERE q.id = ?""",
            (quotation_id,),
        )
        if q is None:
            return None
        q["products"] = QuotationRepository.list_quotation_products(quotation_id)
        return q

    @staticmethod
    def create_quotation(data: dict[str, Any]) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        code = data.get("code", "")
        if not code:
            today = datetime.now().strftime("%Y%m%d")
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT COALESCE(MAX(CAST(SUBSTR(code, -3) AS INTEGER)), 0) + 1 AS seq "
                    "FROM Quotation WHERE code LIKE ?",
                    (f"QUO-{today}-%",),
                )
                row = cursor.fetchone()
                seq = int(row["seq"]) if row else 1
                code = f"QUO-{today}-{seq:03d}"
            finally:
                cursor.close()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO Quotation
                   (code, name, external_name, currency, operation_time, tags,
                    status, pricing_start_date, pricing_end_date, auto_pricing,
                    description, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    code,
                    data["name"],
                    data.get("external_name", ""),
                    data.get("currency", "人民币"),
                    data.get("operation_time", "默认运营时间"),
                    data.get("tags", ""),
                    data.get("status", "active"),
                    data.get("pricing_start_date", ""),
                    data.get("pricing_end_date", ""),
                    1 if data.get("auto_pricing") else 0,
                    data.get("description", ""),
                    now,
                    now,
                ),
            )
            conn.commit()
            qid = cursor.lastrowid

            # Insert associated products
            for p in data.get("products", []):
                QuotationRepository._add_product(cursor, qid, p)
            conn.commit()
            return qid
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def update_quotation(quotation_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            fields = [
                "name", "external_name", "currency", "operation_time", "tags",
                "status", "pricing_start_date", "pricing_end_date",
                "auto_pricing", "description",
            ]
            sets: list[str] = []
            vals: list[Any] = []
            for field in fields:
                if field in data and data[field] is not None:
                    sets.append(f"{field} = ?")
                    val = data[field]
                    if field == "auto_pricing":
                        val = 1 if val else 0
                    vals.append(val)
            if not sets:
                return True
            vals.append(quotation_id)
            cursor.execute(
                f"UPDATE Quotation SET {', '.join(sets)}, updated_at = ? WHERE id = ?",
                vals + [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def toggle_status(quotation_id: int, status: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE Quotation SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), quotation_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # Quotation ↔ Product
    # ------------------------------------------------------------------

    @staticmethod
    def list_quotation_products(quotation_id: int) -> list[dict[str, Any]]:
        return query(
            """SELECT qp.*, p.name AS product_name, p.code AS product_code, p.base_unit
               FROM QuotationProduct qp
               JOIN Product p ON qp.product_id = p.id
               WHERE qp.quotation_id = ?
               ORDER BY qp.id""",
            (quotation_id,),
        )

    @staticmethod
    def add_product(quotation_id: int, product_data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            return QuotationRepository._add_product(cursor, quotation_id, product_data, conn)
        finally:
            cursor.close()

    @staticmethod
    def _add_product(cursor: Any, quotation_id: int, product_data: dict[str, Any],
                     conn: Any = None) -> int:
        cursor.execute(
            """INSERT INTO QuotationProduct (quotation_id, product_id, price)
               VALUES (?, ?, ?)""",
            (quotation_id, product_data["product_id"], product_data.get("price", 0)),
        )
        if conn:
            conn.commit()
        return cursor.lastrowid

    @staticmethod
    def update_product(qp_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            sets: list[str] = []
            vals: list[Any] = []
            if "price" in data and data["price"] is not None:
                sets.append("price = ?")
                vals.append(data["price"])
            if "is_active" in data:
                sets.append("is_active = ?")
                vals.append(1 if data["is_active"] else 0)
            if not sets:
                return True
            vals.append(qp_id)
            cursor.execute(
                f"UPDATE QuotationProduct SET {', '.join(sets)} WHERE id = ?",
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
    def remove_product(qp_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE QuotationProduct SET is_active = 0 WHERE id = ?", (qp_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
