"""Repository helpers for Supplier Settlement."""
from __future__ import annotations

from typing import Any

from app.db.store import get_connection, query, query_one


class SettlementRepository:
    """Persist and query supplier settlement records."""

    @staticmethod
    def create(data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            balance = round(
                data.get("payable_amount", 0)
                - data.get("paid_amount", 0)
                - data.get("fee_amount", 0)
                - data.get("discount_amount", 0),
                2,
            )
            cursor.execute(
                """INSERT INTO SupplierSettlement
                   (supplier_id, settlement_period, payable_amount, paid_amount,
                    fee_amount, discount_amount, balance_amount, remark)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data["supplier_id"],
                    data["settlement_period"],
                    data.get("payable_amount", 0),
                    data.get("paid_amount", 0),
                    data.get("fee_amount", 0),
                    data.get("discount_amount", 0),
                    balance,
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
    def get_by_id(settlement_id: int) -> dict[str, Any] | None:
        return query_one(
            """SELECT ss.*, s.name AS supplier_name
               FROM SupplierSettlement ss
               JOIN Supplier s ON s.id = ss.supplier_id
               WHERE ss.id = ?""",
            (settlement_id,),
        )

    @staticmethod
    def list_settlements(
        *,
        supplier_id: int | None = None,
        period: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if supplier_id:
            clauses.append("ss.supplier_id = ?")
            params.append(supplier_id)
        if period:
            clauses.append("ss.settlement_period = ?")
            params.append(period)
        if status:
            clauses.append("ss.status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return query(
            f"""SELECT ss.*, s.name AS supplier_name
                FROM SupplierSettlement ss
                JOIN Supplier s ON s.id = ss.supplier_id
                {where}
                ORDER BY ss.settlement_period DESC, ss.created_at DESC
                LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        )

    @staticmethod
    def count_settlements(
        *, supplier_id: int | None = None, period: str | None = None, status: str | None = None
    ) -> int:
        clauses = []
        params: list[Any] = []
        if supplier_id:
            clauses.append("supplier_id = ?")
            params.append(supplier_id)
        if period:
            clauses.append("settlement_period = ?")
            params.append(period)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = query_one(
            f"SELECT COUNT(*) AS cnt FROM SupplierSettlement {where}", tuple(params)
        )
        return row["cnt"] if row else 0

    @staticmethod
    def update(settlement_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            sets = []
            vals: list[Any] = []
            for field in ("paid_amount", "fee_amount", "discount_amount", "remark"):
                if field in data and data[field] is not None:
                    sets.append(f"{field} = ?")
                    vals.append(data[field])
            if not sets:
                return True

            # Recalc balance
            current = query_one(
                "SELECT payable_amount, paid_amount, fee_amount, discount_amount FROM SupplierSettlement WHERE id = ?",
                (settlement_id,),
            )
            if current:
                p = data.get("paid_amount", current["paid_amount"])
                f = data.get("fee_amount", current["fee_amount"])
                d = data.get("discount_amount", current["discount_amount"])
                balance = round(current["payable_amount"] - p - f - d, 2)
                sets.append("balance_amount = ?")
                vals.append(balance)

            vals.append(settlement_id)
            cursor.execute(
                f"UPDATE SupplierSettlement SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
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
    def update_status(settlement_id: int, status: str) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE SupplierSettlement SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, settlement_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def get_payable_for_period(supplier_id: int, period: str) -> float:
        """Sum item amounts from confirmed PurchaseInRecord for a period."""
        row = query_one(
            """SELECT COALESCE(SUM(pi.amount), 0) AS total
               FROM PurchaseInRecord r
               JOIN PurchaseInItem pi ON pi.record_id = r.id
               WHERE r.supplier_id = ?
                 AND r.status = 'confirmed'
                 AND r.inbound_date >= ? || '-01'
                 AND r.inbound_date <= ? || '-31'""",
            (supplier_id, period, period),
        )
        return float(row["total"]) if row else 0.0
