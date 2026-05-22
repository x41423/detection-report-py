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
    ) -> int:
        normalized_search = f"%{str(search or '').strip()}%"
        row = query_one(
            """
            SELECT COUNT(*) AS cnt
            FROM InventoryTransaction tx
            JOIN Unit unit ON unit.id = tx.unit_id
            WHERE (? = '%%' OR tx.normalized_name LIKE ? OR tx.display_name LIKE ?)
              AND (? IS NULL OR tx.source_type = ?)
            """,
            (normalized_search, normalized_search, normalized_search, source_type, source_type),
        )
        return row["cnt"] if row else 0

    @staticmethod
    def list_transactions(
        *,
        search: str = "",
        limit: int = 100,
        offset: int = 0,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_search = f"%{str(search or '').strip()}%"
        return query(
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
            WHERE (? = '%%' OR tx.normalized_name LIKE ? OR tx.display_name LIKE ?)
              AND (? IS NULL OR tx.source_type = ?)
            ORDER BY tx.business_date DESC, tx.id DESC
            LIMIT ? OFFSET ?
            """,
            (normalized_search, normalized_search, normalized_search, source_type, source_type, limit, offset),
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
