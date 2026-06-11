"""Weekly Quote 数据访问层"""
from datetime import datetime, timedelta

from app.db.store import run, query, query_one

DEFAULT_WEEKLY_BATCH_LIMIT = 7
DEFAULT_SUMMARY_RULE = "highest"


def _monday_of_week(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def _sunday_of_week(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    sunday = d + timedelta(days=6 - d.weekday())
    return sunday.strftime("%Y-%m-%d")


def week_bounds(date_str: str) -> tuple[str, str]:
    return _monday_of_week(date_str), _sunday_of_week(date_str)


class WeeklyQuoteRepository:
    def get_supplier_configs(self) -> list[dict]:
        self._ensure_historical_supplier_configs()
        rows = query(
            """
            SELECT id, name, weekly_batch_limit, summary_rule, is_builtin, sort_order, created_at, updated_at
            FROM WeeklyQuoteSupplierConfig
            ORDER BY sort_order ASC, id ASC
            """
        )
        return rows

    def get_supplier_config_by_name(self, name: str) -> dict | None:
        normalized = self._normalize_option_name(name)
        if not normalized:
            return None
        self._ensure_historical_supplier_configs()
        return query_one(
            """
            SELECT id, name, weekly_batch_limit, summary_rule, is_builtin, sort_order, created_at, updated_at
            FROM WeeklyQuoteSupplierConfig
            WHERE name = ?
            """,
            (normalized,),
        )

    def upsert_supplier_config(
        self,
        name: str,
        *,
        weekly_batch_limit: int = DEFAULT_WEEKLY_BATCH_LIMIT,
        summary_rule: str = DEFAULT_SUMMARY_RULE,
        is_builtin: bool = False,
        sort_order: int | None = None,
    ) -> dict:
        normalized = self._normalize_option_name(name)
        existing = query_one("SELECT id FROM WeeklyQuoteSupplierConfig WHERE name = ?", (normalized,))
        if sort_order is None:
            sort_order = self._next_sort_order("WeeklyQuoteSupplierConfig")
        if existing:
            run(
                """
                UPDATE WeeklyQuoteSupplierConfig
                SET weekly_batch_limit = ?,
                    summary_rule = ?,
                    is_builtin = ?,
                    sort_order = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (weekly_batch_limit, summary_rule, int(is_builtin), sort_order, existing["id"]),
            )
            return self.get_supplier_config_by_name(normalized)

        run(
            """
            INSERT INTO WeeklyQuoteSupplierConfig (
                name, weekly_batch_limit, summary_rule, is_builtin, sort_order
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (normalized, weekly_batch_limit, summary_rule, int(is_builtin), sort_order),
        )
        return self.get_supplier_config_by_name(normalized)

    def get_measure_unit_options(self) -> list[dict]:
        self._ensure_historical_measure_unit_options()
        return query(
            """
            SELECT id, name, sort_order, created_at, updated_at
            FROM WeeklyQuoteMeasureUnitOption
            ORDER BY sort_order ASC, id ASC
            """
        )

    def get_measure_unit_option_by_name(self, name: str) -> dict | None:
        normalized = self._normalize_option_name(name)
        if not normalized:
            return None
        self._ensure_historical_measure_unit_options()
        return query_one(
            """
            SELECT id, name, sort_order, created_at, updated_at
            FROM WeeklyQuoteMeasureUnitOption
            WHERE name = ?
            """,
            (normalized,),
        )

    def upsert_measure_unit_option(self, name: str, *, sort_order: int | None = None) -> dict:
        normalized = self._normalize_option_name(name)
        existing = query_one("SELECT id FROM WeeklyQuoteMeasureUnitOption WHERE name = ?", (normalized,))
        if sort_order is None:
            sort_order = self._next_sort_order("WeeklyQuoteMeasureUnitOption")
        if existing:
            run(
                """
                UPDATE WeeklyQuoteMeasureUnitOption
                SET sort_order = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (sort_order, existing["id"]),
            )
            return self.get_measure_unit_option_by_name(normalized)

        run(
            """
            INSERT INTO WeeklyQuoteMeasureUnitOption (name, sort_order)
            VALUES (?, ?)
            """,
            (normalized, sort_order),
        )
        return self.get_measure_unit_option_by_name(normalized)

    def ensure_measure_unit_options(self, names: list[str] | tuple[str, ...]) -> None:
        for name in names:
            normalized = self._normalize_option_name(name)
            if not normalized:
                continue
            if query_one("SELECT id FROM WeeklyQuoteMeasureUnitOption WHERE name = ?", (normalized,)):
                continue
            self.upsert_measure_unit_option(normalized)

    def save_batch(self, supplier: str, quote_date: str, entries: list[dict], *,
                   source_label: str = "", source_path: str = "") -> dict:
        existing = query_one(
            "SELECT id FROM WeeklyQuoteBatch WHERE supplier = ? AND quote_date = ?",
            (supplier, quote_date),
        )
        # 空条目 → 删除批次（不留空壳）
        if not entries:
            if existing:
                run("DELETE FROM WeeklyQuoteEntry WHERE batch_id = ?", (existing["id"],))
                run("DELETE FROM WeeklyQuoteBatch WHERE id = ?", (existing["id"],))
            return {"deleted": True, "supplier": supplier, "quote_date": quote_date}

        if existing:
            batch_id = existing["id"]
            run(
                "UPDATE WeeklyQuoteBatch SET source_label = ?, source_path = ? WHERE id = ?",
                (source_label, source_path, batch_id),
            )
            run("DELETE FROM WeeklyQuoteEntry WHERE batch_id = ?", (batch_id,))
        else:
            batch_id = run(
                "INSERT INTO WeeklyQuoteBatch (supplier, quote_date, source_label, source_path) VALUES (?, ?, ?, ?)",
                (supplier, quote_date, source_label, source_path),
            )

        for e in entries:
            run(
                "INSERT INTO WeeklyQuoteEntry (batch_id, name, unit, price) VALUES (?, ?, ?, ?)",
                (batch_id, e["name"], e["unit"], e["price"]),
            )

        return self.get_batch(batch_id)

    def get_batch(self, batch_id: int) -> dict | None:
        batch = query_one("SELECT * FROM WeeklyQuoteBatch WHERE id = ?", (batch_id,))
        if not batch:
            return None
        entries = query("SELECT * FROM WeeklyQuoteEntry WHERE batch_id = ?", (batch_id,))
        batch["entries"] = entries
        batch["entry_count"] = len(entries)
        return batch

    def list_batches(self, supplier: str) -> list[dict]:
        batches = query(
            "SELECT * FROM WeeklyQuoteBatch WHERE supplier = ? ORDER BY quote_date DESC",
            (supplier,),
        )
        return self._attach_entries(batches)

    def list_batches_between(self, supplier: str, date_from: str, date_to: str) -> list[dict]:
        batches = query(
            """
            SELECT * FROM WeeklyQuoteBatch
            WHERE supplier = ? AND quote_date >= ? AND quote_date <= ?
            ORDER BY quote_date ASC
            """,
            (supplier, date_from, date_to),
        )
        return self._attach_entries(batches)

    def list_weekly_batches(self, supplier: str, any_date_in_week: str) -> list[dict]:
        return self.list_batches_between(
            supplier,
            _monday_of_week(any_date_in_week),
            _sunday_of_week(any_date_in_week),
        )

    def list_weekly_batches_for_suppliers(
        self,
        suppliers: list[str] | tuple[str, ...],
        any_date_in_week: str,
    ) -> list[dict]:
        week_start, week_end = week_bounds(any_date_in_week)
        batches: list[dict] = []
        for supplier in suppliers:
            batches.extend(self.list_batches_between(supplier, week_start, week_end))
        batches.sort(key=lambda batch: (batch["supplier"], batch["quote_date"]))
        return batches

    def _attach_entries(self, batches: list[dict]) -> list[dict]:
        for batch in batches:
            entries = query(
                "SELECT * FROM WeeklyQuoteEntry WHERE batch_id = ?", (batch["id"],)
            )
            batch["entries"] = entries
            batch["entry_count"] = len(entries)
        return batches

    def delete_batch(self, supplier: str, quote_date: str) -> bool:
        batch = query_one(
            "SELECT id FROM WeeklyQuoteBatch WHERE supplier = ? AND quote_date = ?",
            (supplier, quote_date),
        )
        if not batch:
            return False
        run("DELETE FROM WeeklyQuoteEntry WHERE batch_id = ?", (batch["id"],))
        run("DELETE FROM WeeklyQuoteBatch WHERE id = ?", (batch["id"],))
        return True

    def get_entries(self, supplier: str, date_from: str, date_to: str) -> list[dict]:
        return query(
            """
            SELECT e.*, b.supplier, b.quote_date, b.source_label
            FROM WeeklyQuoteEntry e
            JOIN WeeklyQuoteBatch b ON e.batch_id = b.id
            WHERE b.supplier = ? AND b.quote_date >= ? AND b.quote_date <= ?
            ORDER BY b.quote_date, e.name
            """,
            (supplier, date_from, date_to),
        )

    def get_weekly_summary(self, supplier: str, any_date_in_week: str) -> list[dict]:
        batches = self.list_weekly_batches(supplier, any_date_in_week)
        if not batches:
            return []

        from app.utils.weekly_quote_summary import preview_weekly_quote_summary

        summary = preview_weekly_quote_summary(
            [
                {
                    "supplier": batch["supplier"],
                    "quote_date": batch["quote_date"],
                    "entries": batch["entries"],
                }
                for batch in batches
            ],
            supplier_configs=self.get_supplier_configs(),
        )
        unit_summary = next(
            (item for item in summary["unit_summaries"] if item["supplier"] == supplier),
            None,
        )
        if not unit_summary:
            return []
        return unit_summary["summary_items"]

    def get_all_suppliers(self) -> list[str]:
        rows = query("SELECT DISTINCT supplier FROM WeeklyQuoteBatch ORDER BY supplier")
        return [r["supplier"] for r in rows]

    def _ensure_historical_supplier_configs(self) -> None:
        rows = query(
            """
            SELECT DISTINCT supplier AS name
            FROM WeeklyQuoteBatch
            WHERE supplier IS NOT NULL AND TRIM(supplier) != ''
            ORDER BY supplier
            """
        )
        for row in rows:
            name = self._normalize_option_name(row["name"])
            if not name:
                continue
            if query_one("SELECT id FROM WeeklyQuoteSupplierConfig WHERE name = ?", (name,)):
                continue
            self.upsert_supplier_config(
                name,
                weekly_batch_limit=DEFAULT_WEEKLY_BATCH_LIMIT,
                summary_rule=DEFAULT_SUMMARY_RULE,
                is_builtin=False,
            )

    def _ensure_historical_measure_unit_options(self) -> None:
        rows = query(
            """
            SELECT DISTINCT unit AS name
            FROM WeeklyQuoteEntry
            WHERE unit IS NOT NULL AND TRIM(unit) != ''
            ORDER BY unit
            """
        )
        for row in rows:
            name = self._normalize_option_name(row["name"])
            if not name:
                continue
            if query_one("SELECT id FROM WeeklyQuoteMeasureUnitOption WHERE name = ?", (name,)):
                continue
            self.upsert_measure_unit_option(name)

    def _next_sort_order(self, table_name: str) -> int:
        row = query_one(f"SELECT COALESCE(MAX(sort_order), 0) AS max_sort_order FROM {table_name}")
        return int(row["max_sort_order"] or 0) + 10

    def _normalize_option_name(self, name: str) -> str:
        return str(name or "").strip()
