"""Repository helpers for the daily-intake domain."""

from __future__ import annotations

from typing import Any

from app.db.inventory_repository import InventoryRepository
from app.db.store import get_connection, query, query_one


class DailyIntakeRepository:
    """Persist and retrieve daily-intake sheets and items."""

    @staticmethod
    def get_sheet_by_date(intake_date: str, create_if_missing: bool = True) -> dict[str, Any] | None:
        if create_if_missing:
            DailyIntakeRepository._ensure_sheet_exists(intake_date)

        sheet = query_one(
            """
            SELECT id, intake_date, status, created_at, updated_at
            FROM DailyIntakeSheet
            WHERE intake_date = ?
            """,
            (intake_date,),
        )
        if not sheet:
            return None

        items = query(
            """
            SELECT
                item.id,
                item.sheet_id,
                item.veg_id,
                item.raw_name,
                item.normalized_name,
                item.category,
                item.unit_id,
                unit.name AS unit_name,
                item.quantity,
                item.source,
                item.transcript,
                item.last_source,
                item.last_transcript,
                item.merge_count,
                item.last_confirmed_at,
                item.created_at,
                item.updated_at
            FROM DailyIntakeItem item
            JOIN Unit unit ON unit.id = item.unit_id
            WHERE item.sheet_id = ?
            ORDER BY item.updated_at DESC, item.id DESC
            """,
            (sheet["id"],),
        )

        sheet["items"] = items
        sheet["item_count"] = len(items)
        sheet["total_quantity"] = round(sum(float(item["quantity"]) for item in items), 2)
        qty_by_unit: dict[str, float] = {}
        for _item in items:
            _u = _item["unit_name"]
            qty_by_unit[_u] = round(qty_by_unit.get(_u, 0.0) + float(_item["quantity"]), 2)
        sheet["quantity_by_unit"] = qty_by_unit
        sheet["category_counts"] = DailyIntakeRepository._count_categories(items)
        return sheet

    @staticmethod
    def list_history(limit: int = 30) -> list[dict[str, Any]]:
        return query(
            """
            SELECT
                sheet.id,
                sheet.intake_date,
                sheet.status,
                sheet.created_at,
                sheet.updated_at,
                COUNT(item.id) AS item_count,
                COALESCE(SUM(item.quantity), 0) AS total_quantity
            FROM DailyIntakeSheet sheet
            LEFT JOIN DailyIntakeItem item ON item.sheet_id = sheet.id
            GROUP BY sheet.id
            HAVING COUNT(item.id) > 0
            ORDER BY sheet.intake_date DESC
            LIMIT ?
            """,
            (limit,),
        )

    @staticmethod
    def find_merge_candidate(
        intake_date: str,
        normalized_name: str,
        unit_name: str,
    ) -> dict[str, Any] | None:
        sheet = query_one(
            """
            SELECT id
            FROM DailyIntakeSheet
            WHERE intake_date = ?
            """,
            (intake_date,),
        )
        if not sheet:
            return None

        return query_one(
            """
            SELECT
                item.id,
                item.quantity,
                item.merge_count,
                unit.name AS unit_name
            FROM DailyIntakeItem item
            JOIN Unit unit ON unit.id = item.unit_id
            WHERE item.sheet_id = ? AND item.normalized_name = ? AND unit.name = ?
            """,
            (sheet["id"], normalized_name, unit_name),
        )

    @staticmethod
    def add_or_merge_item(
        *,
        intake_date: str,
        raw_name: str,
        normalized_name: str,
        category: str,
        unit_name: str,
        quantity: float,
        source: str,
        transcript: str,
        last_confirmed_at: str,
        veg_id: int | None,
    ) -> dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN IMMEDIATE")
            sheet = DailyIntakeRepository._get_or_create_sheet_row(cursor, intake_date)
            unit_id = DailyIntakeRepository._get_or_create_unit_id(cursor, unit_name)
            existing = cursor.execute(
                """
                SELECT id, quantity, category, veg_id, merge_count, transcript
                FROM DailyIntakeItem
                WHERE sheet_id = ? AND normalized_name = ? AND unit_id = ?
                """,
                (sheet["id"], normalized_name, unit_id),
            ).fetchone()

            if existing:
                merged = True
                target_item_id = int(existing["id"])
                next_quantity = round(float(existing["quantity"]) + float(quantity), 2)
                next_category = existing["category"] or category
                next_veg_id = existing["veg_id"] if existing["veg_id"] is not None else veg_id
                _existing_tx = str(existing["transcript"] or "").strip()
                _new_tx = str(transcript or "").strip()
                accumulated_transcript = "\n---\n".join(t for t in [_existing_tx, _new_tx] if t)
                cursor.execute(
                    """
                    UPDATE DailyIntakeItem
                    SET raw_name = ?,
                        normalized_name = ?,
                        category = ?,
                        veg_id = ?,
                        quantity = ?,
                        source = ?,
                        transcript = ?,
                        last_source = ?,
                        last_transcript = ?,
                        merge_count = ?,
                        last_confirmed_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        raw_name,
                        normalized_name,
                        next_category,
                        next_veg_id,
                        next_quantity,
                        source,
                        accumulated_transcript,
                        source,
                        _new_tx or _existing_tx,
                        int(existing["merge_count"]) + 1,
                        last_confirmed_at,
                        target_item_id,
                    ),
                )
                inventory_quantity = next_quantity
            else:
                merged = False
                cursor.execute(
                    """
                    INSERT INTO DailyIntakeItem (
                        sheet_id,
                        veg_id,
                        raw_name,
                        normalized_name,
                        category,
                        unit_id,
                        quantity,
                        source,
                        transcript,
                        last_source,
                        last_transcript,
                        merge_count,
                        last_confirmed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sheet["id"],
                        veg_id,
                        raw_name,
                        normalized_name,
                        category,
                        unit_id,
                        quantity,
                        source,
                        transcript,
                        source,
                        transcript,
                        1,
                        last_confirmed_at,
                    ),
                )
                target_item_id = int(cursor.lastrowid)
                inventory_quantity = float(quantity)

            InventoryRepository.upsert_daily_intake_stock_in_with_cursor(
                cursor,
                source_ref_id=target_item_id,
                business_date=intake_date,
                display_name=raw_name,
                normalized_name=normalized_name,
                veg_id=next_veg_id if existing else veg_id,
                unit_name=unit_name,
                quantity=inventory_quantity,
            )

            DailyIntakeRepository._touch_sheet(cursor, sheet["id"])
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

        return {
            "sheet": DailyIntakeRepository.get_sheet_by_date(intake_date, create_if_missing=False),
            "item_id": target_item_id,
            "merged": merged,
        }

    @staticmethod
    def update_item(
        *,
        item_id: int,
        raw_name: str,
        normalized_name: str,
        category: str,
        unit_name: str,
        quantity: float,
        source: str,
        transcript: str,
        last_confirmed_at: str,
        veg_id: int | None,
    ) -> dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN IMMEDIATE")
            current = cursor.execute(
                """
                SELECT
                    item.id,
                    item.sheet_id,
                    item.merge_count,
                    item.transcript AS item_transcript,
                    sheet.intake_date
                FROM DailyIntakeItem item
                JOIN DailyIntakeSheet sheet ON sheet.id = item.sheet_id
                WHERE item.id = ?
                """,
                (item_id,),
            ).fetchone()
            if not current:
                raise KeyError("未找到待更新的点货条目")

            unit_id = DailyIntakeRepository._get_or_create_unit_id(cursor, unit_name)
            duplicate = cursor.execute(
                """
                SELECT id, quantity, category, veg_id, merge_count, transcript
                FROM DailyIntakeItem
                WHERE sheet_id = ? AND normalized_name = ? AND unit_id = ? AND id != ?
                """,
                (current["sheet_id"], normalized_name, unit_id, item_id),
            ).fetchone()

            if duplicate:
                merged = True
                target_item_id = int(duplicate["id"])
                merged_quantity = round(float(duplicate["quantity"]) + float(quantity), 2)
                merged_veg_id = duplicate["veg_id"] if duplicate["veg_id"] is not None else veg_id
                _dup_tx = str(duplicate["transcript"] or "").strip()
                _cur_tx = str(current["item_transcript"] or "").strip()
                _new_tx = str(transcript or "").strip()
                _edit_accumulated = "\n---\n".join(t for t in [_dup_tx, _cur_tx] if t)
                cursor.execute(
                    """
                    UPDATE DailyIntakeItem
                    SET raw_name = ?,
                        normalized_name = ?,
                        category = ?,
                        veg_id = ?,
                        quantity = ?,
                        source = ?,
                        transcript = ?,
                        last_source = ?,
                        last_transcript = ?,
                        merge_count = ?,
                        last_confirmed_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        raw_name,
                        normalized_name,
                        duplicate["category"] or category,
                        merged_veg_id,
                        merged_quantity,
                        source,
                        _edit_accumulated,
                        source,
                        _new_tx or _cur_tx or _dup_tx,
                        int(duplicate["merge_count"]) + int(current["merge_count"]),
                        last_confirmed_at,
                        target_item_id,
                    ),
                )
                cursor.execute("DELETE FROM DailyIntakeItem WHERE id = ?", (item_id,))
                InventoryRepository.upsert_daily_intake_stock_in_with_cursor(
                    cursor,
                    source_ref_id=target_item_id,
                    business_date=current["intake_date"],
                    display_name=raw_name,
                    normalized_name=normalized_name,
                    veg_id=merged_veg_id,
                    unit_name=unit_name,
                    quantity=merged_quantity,
                )
                InventoryRepository.delete_daily_intake_stock_in_with_cursor(cursor, item_id)
            else:
                merged = False
                target_item_id = int(item_id)
                cursor.execute(
                    """
                    UPDATE DailyIntakeItem
                    SET raw_name = ?,
                        normalized_name = ?,
                        category = ?,
                        veg_id = ?,
                        unit_id = ?,
                        quantity = ?,
                        source = ?,
                        last_source = ?,
                        last_transcript = ?,
                        last_confirmed_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        raw_name,
                        normalized_name,
                        category,
                        veg_id,
                        unit_id,
                        quantity,
                        source,
                        source,
                        transcript,
                        last_confirmed_at,
                        item_id,
                    ),
                )
                InventoryRepository.upsert_daily_intake_stock_in_with_cursor(
                    cursor,
                    source_ref_id=target_item_id,
                    business_date=current["intake_date"],
                    display_name=raw_name,
                    normalized_name=normalized_name,
                    veg_id=veg_id,
                    unit_name=unit_name,
                    quantity=float(quantity),
                )

            DailyIntakeRepository._touch_sheet(cursor, current["sheet_id"])
            conn.commit()
            intake_date = current["intake_date"]
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

        return {
            "sheet": DailyIntakeRepository.get_sheet_by_date(intake_date, create_if_missing=False),
            "item_id": target_item_id,
            "merged": merged,
        }

    @staticmethod
    def delete_item(item_id: int) -> dict[str, Any]:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN IMMEDIATE")
            item = cursor.execute(
                """
                SELECT item.id, item.sheet_id, sheet.intake_date
                FROM DailyIntakeItem item
                JOIN DailyIntakeSheet sheet ON sheet.id = item.sheet_id
                WHERE item.id = ?
                """,
                (item_id,),
            ).fetchone()
            if not item:
                raise KeyError("未找到待删除的点货条目")

            cursor.execute("DELETE FROM DailyIntakeItem WHERE id = ?", (item_id,))
            InventoryRepository.delete_daily_intake_stock_in_with_cursor(cursor, item_id)
            DailyIntakeRepository._touch_sheet(cursor, item["sheet_id"])
            conn.commit()
            intake_date = item["intake_date"]
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

        return {
            "sheet": DailyIntakeRepository.get_sheet_by_date(intake_date, create_if_missing=False),
        }

    @staticmethod
    def _ensure_sheet_exists(intake_date: str) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT OR IGNORE INTO DailyIntakeSheet (intake_date)
                VALUES (?)
                """,
                (intake_date,),
            )
            conn.commit()
        finally:
            cursor.close()

    @staticmethod
    def _get_or_create_sheet_row(cursor, intake_date: str):
        row = cursor.execute(
            """
            SELECT id, intake_date, status, created_at, updated_at
            FROM DailyIntakeSheet
            WHERE intake_date = ?
            """,
            (intake_date,),
        ).fetchone()
        if row:
            return row

        cursor.execute(
            """
            INSERT INTO DailyIntakeSheet (intake_date)
            VALUES (?)
            """,
            (intake_date,),
        )
        return cursor.execute(
            """
            SELECT id, intake_date, status, created_at, updated_at
            FROM DailyIntakeSheet
            WHERE intake_date = ?
            """,
            (intake_date,),
        ).fetchone()

    @staticmethod
    def _get_or_create_unit_id(cursor, unit_name: str) -> int:
        row = cursor.execute("SELECT id FROM Unit WHERE name = ?", (unit_name,)).fetchone()
        if row:
            return int(row["id"])

        cursor.execute("INSERT INTO Unit (name) VALUES (?)", (unit_name,))
        return int(cursor.lastrowid)

    @staticmethod
    def _touch_sheet(cursor, sheet_id: int) -> None:
        cursor.execute(
            """
            UPDATE DailyIntakeSheet
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (sheet_id,),
        )

    @staticmethod
    def _count_categories(items: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"vegetable": 0, "frozen": 0, "meat": 0}
        for item in items:
            category = item.get("category")
            if category in counts:
                counts[category] += 1
        return counts
