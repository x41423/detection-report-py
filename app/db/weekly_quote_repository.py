"""Weekly Quote 数据访问层"""
from datetime import datetime, timedelta

from app.db.store import run, query, query_one


def _monday_of_week(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    monday = d - timedelta(days=d.weekday())
    return monday.strftime("%Y-%m-%d")


def _sunday_of_week(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d")
    sunday = d + timedelta(days=6 - d.weekday())
    return sunday.strftime("%Y-%m-%d")


class WeeklyQuoteRepository:

    def save_batch(self, supplier: str, quote_date: str, entries: list[dict], *,
                   source_label: str = "", source_path: str = "") -> dict:
        existing = query_one(
            "SELECT id FROM WeeklyQuoteBatch WHERE supplier = ? AND quote_date = ?",
            (supplier, quote_date),
        )
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
        monday = _monday_of_week(any_date_in_week)
        sunday = _sunday_of_week(any_date_in_week)
        return query(
            """
            SELECT e.name, e.unit, MAX(e.price) as summary_price
            FROM WeeklyQuoteEntry e
            JOIN WeeklyQuoteBatch b ON e.batch_id = b.id
            WHERE b.supplier = ? AND b.quote_date >= ? AND b.quote_date <= ?
            GROUP BY e.name, e.unit
            ORDER BY e.name
            """,
            (supplier, monday, sunday),
        )

    def get_all_suppliers(self) -> list[str]:
        rows = query("SELECT DISTINCT supplier FROM WeeklyQuoteBatch ORDER BY supplier")
        return [r["supplier"] for r in rows]
