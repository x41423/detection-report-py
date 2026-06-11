"""Repository helpers for inventory transactions and balances."""

from __future__ import annotations

from typing import Any

from app.db.store import get_connection, query, query_one


class InventoryRepository:
    """Persist and query inventory transactions."""

    DAILY_INTAKE_SOURCE = "daily_intake"
    OUTBOUND_SOURCE = "manual_outbound"
    ADJUST_SOURCE = "manual_adjust"

    @staticmethod
    def list_balances(
        *,
        search: str = "",
        limit: int = 200,
        include_zero: bool = False,
    ) -> list[dict[str, Any]]:
        normalized_search = f"%{str(search or '').strip()}%"
        return query(
            """
            SELECT
                COALESCE(MAX(tx.display_name), tx.normalized_name) AS display_name,
                tx.normalized_name,
                MAX(tx.veg_id) AS veg_id,
                tx.unit_id,
                unit.name AS unit_name,
                ROUND(SUM(tx.quantity_delta), 3) AS available_quantity,
                COUNT(tx.id) AS transaction_count,
                MAX(tx.business_date) AS last_business_date,
                MAX(tx.updated_at) AS updated_at
            FROM InventoryTransaction tx
            JOIN Unit unit ON unit.id = tx.unit_id
            WHERE (? = '%%' OR tx.normalized_name LIKE ? OR tx.display_name LIKE ?)
            GROUP BY tx.normalized_name, tx.unit_id, unit.name
            HAVING (? = 1 OR ABS(SUM(tx.quantity_delta)) > 0.000001)
            ORDER BY MAX(tx.updated_at) DESC, tx.normalized_name ASC
            LIMIT ?
            """,
            (normalized_search, normalized_search, normalized_search, int(include_zero), limit),
        )

    @staticmethod
    def count_transactions(
        *,
        search: str = "",
        source_type: str | None = None,
        direction: str | None = None,
        date_from: str = "",
        date_to: str = "",
    ) -> int:
        normalized_search = f"%{str(search or '').strip()}%"
        where_parts = [
            "(? = '%%' OR tx.normalized_name LIKE ? OR tx.display_name LIKE ?)",
        ]
        params: list[Any] = [normalized_search, normalized_search, normalized_search]

        if source_type:
            where_parts.append("tx.source_type = ?")
            params.append(source_type)
        if direction:
            where_parts.append("tx.direction = ?")
            params.append(direction)
        if date_from.strip():
            where_parts.append("tx.business_date >= ?")
            params.append(date_from.strip())
        if date_to.strip():
            where_parts.append("tx.business_date <= ?")
            params.append(date_to.strip())

        where = " AND ".join(where_parts)
        row = query_one(
            f"SELECT COUNT(*) AS cnt FROM InventoryTransaction tx JOIN Unit unit ON unit.id = tx.unit_id WHERE {where}",
            params,
        )
        return row["cnt"] if row else 0

    @staticmethod
    def list_transactions(
        *,
        search: str = "",
        limit: int = 100,
        offset: int = 0,
        source_type: str | None = None,
        direction: str | None = None,
        date_from: str = "",
        date_to: str = "",
    ) -> list[dict[str, Any]]:
        normalized_search = f"%{str(search or '').strip()}%"
        where_parts = [
            "(? = '%%' OR tx.normalized_name LIKE ? OR tx.display_name LIKE ?)",
        ]
        params: list[Any] = [normalized_search, normalized_search, normalized_search]

        if source_type:
            where_parts.append("tx.source_type = ?")
            params.append(source_type)
        if direction:
            where_parts.append("tx.direction = ?")
            params.append(direction)
        if date_from.strip():
            where_parts.append("tx.business_date >= ?")
            params.append(date_from.strip())
        if date_to.strip():
            where_parts.append("tx.business_date <= ?")
            params.append(date_to.strip())

        where = " AND ".join(where_parts)
        params.extend([limit, offset])
        return query(
            f"""SELECT tx.id, tx.veg_id, tx.display_name, tx.normalized_name,
                       tx.unit_id, unit.name AS unit_name,
                       tx.direction, tx.quantity_delta, ABS(tx.quantity_delta) AS quantity,
                       tx.business_date, tx.source_type, tx.source_ref_id,
                       tx.note, tx.created_at, tx.updated_at
                FROM InventoryTransaction tx
                JOIN Unit unit ON unit.id = tx.unit_id
                WHERE {where}
                ORDER BY tx.business_date DESC, tx.id DESC
                LIMIT ? OFFSET ?""",
            params,
        )

    @staticmethod
    def get_transaction(transaction_id: int) -> dict[str, Any] | None:
        return query_one(
            """
            SELECT
                tx.id,
                tx.veg_id,
                tx.display_name,
                tx.normalized_name,
                tx.unit_id,
                unit.name AS unit_name,
                tx.direction,
                tx.quantity_delta,
                ABS(tx.quantity_delta) AS quantity,
                tx.business_date,
                tx.source_type,
                tx.source_ref_id,
                tx.note,
                tx.created_at,
                tx.updated_at
            FROM InventoryTransaction tx
            JOIN Unit unit ON unit.id = tx.unit_id
            WHERE tx.id = ?
            """,
            (transaction_id,),
        )

    @staticmethod
    def get_current_balance(
        normalized_name: str,
        unit_name: str,
        *,
        exclude_transaction_id: int | None = None,
    ) -> float:
        unit = query_one("SELECT id FROM Unit WHERE name = ?", (unit_name,))
        if not unit:
            return 0.0

        sql = """
            SELECT COALESCE(SUM(quantity_delta), 0) AS balance
            FROM InventoryTransaction
            WHERE normalized_name = ? AND unit_id = ?
        """
        params: list[Any] = [normalized_name, int(unit["id"])]
        if exclude_transaction_id is not None:
            sql += " AND id != ?"
            params.append(exclude_transaction_id)

        row = query_one(sql, tuple(params))
        return float(row["balance"]) if row else 0.0

    @staticmethod
    def create_manual_transaction(
        *,
        display_name: str,
        normalized_name: str,
        veg_id: int | None,
        unit_name: str,
        direction: str,
        quantity_delta: float,
        business_date: str,
        source_type: str,
        note: str = "",
    ) -> dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN IMMEDIATE")
            unit_id = InventoryRepository._get_or_create_unit_id(cursor, unit_name)
            cursor.execute(
                """
                INSERT INTO InventoryTransaction (
                    veg_id,
                    display_name,
                    normalized_name,
                    unit_id,
                    direction,
                    quantity_delta,
                    business_date,
                    source_type,
                    source_ref_id,
                    note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    veg_id,
                    display_name,
                    normalized_name,
                    unit_id,
                    direction,
                    quantity_delta,
                    business_date,
                    source_type,
                    note,
                ),
            )
            transaction_id = int(cursor.lastrowid)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

        return InventoryRepository.get_transaction(transaction_id) or {}

    @staticmethod
    def update_manual_transaction(
        transaction_id: int,
        *,
        display_name: str,
        normalized_name: str,
        veg_id: int | None,
        unit_name: str,
        direction: str,
        quantity_delta: float,
        business_date: str,
        note: str = "",
    ) -> dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN IMMEDIATE")
            unit_id = InventoryRepository._get_or_create_unit_id(cursor, unit_name)
            cursor.execute(
                """
                UPDATE InventoryTransaction
                SET veg_id = ?,
                    display_name = ?,
                    normalized_name = ?,
                    unit_id = ?,
                    direction = ?,
                    quantity_delta = ?,
                    business_date = ?,
                    note = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    veg_id,
                    display_name,
                    normalized_name,
                    unit_id,
                    direction,
                    quantity_delta,
                    business_date,
                    note,
                    transaction_id,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

        return InventoryRepository.get_transaction(transaction_id) or {}

    @staticmethod
    def delete_transaction(transaction_id: int) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("DELETE FROM InventoryTransaction WHERE id = ?", (transaction_id,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def backfill_missing_daily_intake_transactions() -> int:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN IMMEDIATE")
            missing_rows = cursor.execute(
                """
                SELECT
                    item.id AS source_ref_id,
                    sheet.intake_date AS business_date,
                    item.raw_name AS display_name,
                    item.normalized_name,
                    item.veg_id,
                    unit.name AS unit_name,
                    item.quantity
                FROM DailyIntakeItem item
                JOIN DailyIntakeSheet sheet ON sheet.id = item.sheet_id
                JOIN Unit unit ON unit.id = item.unit_id
                LEFT JOIN InventoryTransaction tx
                    ON tx.source_type = ?
                   AND tx.source_ref_id = item.id
                WHERE tx.id IS NULL
                ORDER BY item.id ASC
                """,
                (InventoryRepository.DAILY_INTAKE_SOURCE,),
            ).fetchall()

            for row in missing_rows:
                InventoryRepository.upsert_daily_intake_stock_in_with_cursor(
                    cursor,
                    source_ref_id=int(row["source_ref_id"]),
                    business_date=row["business_date"],
                    display_name=row["display_name"],
                    normalized_name=row["normalized_name"],
                    veg_id=row["veg_id"],
                    unit_name=row["unit_name"],
                    quantity=float(row["quantity"]),
                )

            conn.commit()
            return len(missing_rows)
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def upsert_daily_intake_stock_in_with_cursor(
        cursor,
        *,
        source_ref_id: int,
        business_date: str,
        display_name: str,
        normalized_name: str,
        veg_id: int | None,
        unit_name: str,
        quantity: float,
    ) -> None:
        unit_id = InventoryRepository._get_or_create_unit_id(cursor, unit_name)
        existing = cursor.execute(
            """
            SELECT id
            FROM InventoryTransaction
            WHERE source_type = ? AND source_ref_id = ?
            """,
            (InventoryRepository.DAILY_INTAKE_SOURCE, source_ref_id),
        ).fetchone()

        payload = (
            veg_id,
            display_name,
            normalized_name,
            unit_id,
            "IN",
            float(quantity),
            business_date,
            InventoryRepository.DAILY_INTAKE_SOURCE,
            source_ref_id,
            "",
        )
        if existing:
            cursor.execute(
                """
                UPDATE InventoryTransaction
                SET veg_id = ?,
                    display_name = ?,
                    normalized_name = ?,
                    unit_id = ?,
                    direction = ?,
                    quantity_delta = ?,
                    business_date = ?,
                    source_type = ?,
                    source_ref_id = ?,
                    note = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (*payload, int(existing["id"])),
            )
            return

        cursor.execute(
            """
            INSERT INTO InventoryTransaction (
                veg_id,
                display_name,
                normalized_name,
                unit_id,
                direction,
                quantity_delta,
                business_date,
                source_type,
                source_ref_id,
                note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )

    @staticmethod
    def delete_daily_intake_stock_in_with_cursor(cursor, source_ref_id: int) -> None:
        cursor.execute(
            """
            DELETE FROM InventoryTransaction
            WHERE source_type = ? AND source_ref_id = ?
            """,
            (InventoryRepository.DAILY_INTAKE_SOURCE, source_ref_id),
        )

    @staticmethod
    def _get_or_create_unit_id(cursor, unit_name: str) -> int:
        row = cursor.execute("SELECT id FROM Unit WHERE name = ?", (unit_name,)).fetchone()
        if row:
            return int(row["id"])

        cursor.execute("INSERT INTO Unit (name) VALUES (?)", (unit_name,))
        return int(cursor.lastrowid)

    # ------------------------------------------------------------------
    # Step 3 — 库存扩展: 跨表只读查询
    # ------------------------------------------------------------------

    @staticmethod
    def get_stock_alerts(*, threshold: float = 10.0, limit: int = 50) -> list[dict[str, Any]]:
        """Return items whose available_quantity is <= threshold, sorted by urgency."""
        return query(
            """SELECT
                tx.display_name,
                tx.normalized_name,
                u.name AS unit_name,
                COALESCE(SUM(CASE WHEN tx.direction = 'IN'  THEN tx.quantity_delta ELSE 0 END), 0)
                - COALESCE(SUM(CASE WHEN tx.direction = 'OUT' THEN tx.quantity_delta ELSE 0 END), 0)
                AS available_quantity
            FROM InventoryTransaction tx
            JOIN Unit u ON u.id = tx.unit_id
            GROUP BY tx.normalized_name
            HAVING available_quantity <= ?
            ORDER BY available_quantity ASC
            LIMIT ?""",
            (threshold, limit),
        )

    @staticmethod
    def get_transaction_summary(
        *, start_date: str | None = None, end_date: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Return transaction list with supplier name joined from purchase records."""
        clauses = []
        params: list[Any] = []
        if start_date:
            clauses.append("tx.business_date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("tx.business_date <= ?")
            params.append(end_date)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return query(
            f"""SELECT
                tx.id,
                tx.display_name,
                tx.normalized_name,
                u.name AS unit_name,
                tx.direction,
                tx.quantity_delta,
                tx.business_date,
                tx.source_type,
                tx.note,
                COALESCE(pin.order_no, prt.order_no, ord.order_no, '') AS related_order_no,
                COALESCE(s.name, ord.merchant_name, '') AS supplier_name
            FROM InventoryTransaction tx
            JOIN Unit u ON u.id = tx.unit_id
            LEFT JOIN PurchaseInItem pii ON pii.id = tx.source_ref_id AND tx.source_type = 'purchase_in'
            LEFT JOIN PurchaseInRecord pin ON pin.id = pii.record_id
            LEFT JOIN PurchaseReturnItem pri ON pri.id = tx.source_ref_id AND tx.source_type = 'purchase_return'
            LEFT JOIN PurchaseReturnRecord prt ON prt.id = pri.record_id
            LEFT JOIN OrderItem oi ON oi.id = tx.source_ref_id AND tx.source_type = 'purchase_outbound'
            LEFT JOIN OrderRecord ord ON ord.id = oi.order_id
            LEFT JOIN Supplier s ON s.id = COALESCE(pin.supplier_id, prt.supplier_id)
            {where}
            ORDER BY tx.business_date DESC, tx.id DESC
            LIMIT ?""",
            (*params, limit),
        )

    @staticmethod
    def count_transaction_summary(*, start_date: str | None = None, end_date: str | None = None) -> int:
        clauses = []
        params: list[Any] = []
        if start_date:
            clauses.append("tx.business_date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("tx.business_date <= ?")
            params.append(end_date)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = query_one(
            f"""SELECT COUNT(*) AS cnt
            FROM InventoryTransaction tx
            LEFT JOIN PurchaseInItem pii ON pii.id = tx.source_ref_id AND tx.source_type = 'purchase_in'
            LEFT JOIN PurchaseInRecord pin ON pin.id = pii.record_id
            LEFT JOIN PurchaseReturnItem pri ON pri.id = tx.source_ref_id AND tx.source_type = 'purchase_return'
            LEFT JOIN PurchaseReturnRecord prt ON prt.id = pri.record_id
            LEFT JOIN OrderItem oi ON oi.id = tx.source_ref_id AND tx.source_type = 'purchase_outbound'
            LEFT JOIN OrderRecord ord ON ord.id = oi.order_id
            {where}""",
            tuple(params),
        )
        return row["cnt"] if row else 0
