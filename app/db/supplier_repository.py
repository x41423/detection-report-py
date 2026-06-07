"""Repository helpers for Supplier CRUD operations."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.db.store import get_connection, query, query_one


class SupplierRepository:
    """Persist and query supplier records.

    All methods are static to match the InventoryRepository convention.
    """

    @staticmethod
    def _generate_code(cursor: Any) -> str:
        """Generate a unique supplier code: SUP-YYYYMMDD-NNN."""
        today = date.today().strftime("%Y%m%d")
        cursor.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(code, -3) AS INTEGER)), 0) + 1 AS seq "
            "FROM Supplier WHERE code LIKE ?",
            (f"SUP-{today}-%",),
        )
        row = cursor.fetchone()
        seq = int(row["seq"]) if row else 1
        return f"SUP-{today}-{seq:03d}"

    @staticmethod
    def create(data: dict[str, Any]) -> int:
        """Insert a new supplier and return its id.  Code is auto-generated."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            code = SupplierRepository._generate_code(cursor)
            cursor.execute(
                """INSERT INTO Supplier (code, name, contact_person, contact_phone,
                   contact_address, supplier_type, business_license, tax_number,
                   bank_name, bank_account, settlement_method, payment_terms,
                   credit_limit, level,
                   settlement_person, settlement_phone, date_dimension,
                   period_start_day, settlement_day, freeze_status,
                   approval_status, sorting_priority, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    code,
                    data["name"],
                    data.get("contact_person"),
                    data.get("contact_phone"),
                    data.get("contact_address"),
                    data.get("supplier_type", "enterprise"),
                    data.get("business_license"),
                    data.get("tax_number"),
                    data.get("bank_name"),
                    data.get("bank_account"),
                    data.get("settlement_method", "monthly"),
                    data.get("payment_terms"),
                    data.get("credit_limit", 0),
                    data.get("level", "normal"),
                    data.get("settlement_person"),
                    data.get("settlement_phone"),
                    data.get("date_dimension", "order_date"),
                    data.get("period_start_day", 1),
                    data.get("settlement_day", 1),
                    data.get("freeze_status", 0),
                    data.get("approval_status", 1),
                    data.get("sorting_priority", 0),
                    data.get("remark"),
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
    def get_by_id(supplier_id: int) -> dict[str, Any] | None:
        return query_one("SELECT * FROM Supplier WHERE id = ?", (supplier_id,))

    @staticmethod
    def list(
        *,
        search: str = "",
        status: str | None = None,
        supplier_type: str | None = None,
        level: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        normalized = f"%{search.strip()}%"
        clauses = ["(name LIKE ? OR code LIKE ?)"]
        params: list[Any] = [normalized, normalized]

        if status:
            clauses.append("status = ?")
            params.append(status)
        if supplier_type:
            clauses.append("supplier_type = ?")
            params.append(supplier_type)
        if level:
            clauses.append("level = ?")
            params.append(level)

        where = " AND ".join(clauses)
        return query(
            f"SELECT * FROM Supplier WHERE {where} "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )

    @staticmethod
    def count(*, search: str = "", status: str | None = None, supplier_type: str | None = None, level: str | None = None) -> int:
        normalized = f"%{search.strip()}%"
        clauses = ["(name LIKE ? OR code LIKE ?)"]
        params: list[Any] = [normalized, normalized]

        if status:
            clauses.append("status = ?")
            params.append(status)
        if supplier_type:
            clauses.append("supplier_type = ?")
            params.append(supplier_type)
        if level:
            clauses.append("level = ?")
            params.append(level)

        where = " AND ".join(clauses)
        row = query_one(f"SELECT COUNT(*) AS cnt FROM Supplier WHERE {where}", tuple(params))
        return row["cnt"] if row else 0

    @staticmethod
    def update(supplier_id: int, data: dict[str, Any]) -> bool:
        """Partial update — only provided fields are changed."""
        if not data:
            return False
        sets = [f"{key} = ?" for key in data]
        values = list(data.values())
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"UPDATE Supplier SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (*values, supplier_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def deactivate(supplier_id: int) -> bool:
        """Soft-delete: set status to 'inactive'."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE Supplier SET status = 'inactive', updated_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (supplier_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def has_purchase_records(supplier_id: int) -> bool:
        """Check whether the supplier has any linked purchase records."""
        row = query_one(
            "SELECT COUNT(*) AS cnt FROM PurchaseInRecord WHERE supplier_id = ?",
            (supplier_id,),
        )
        return bool(row and row["cnt"] > 0)
