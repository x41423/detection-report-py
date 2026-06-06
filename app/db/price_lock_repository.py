"""Repository helpers for Price Lock rules."""
from __future__ import annotations

from typing import Any

from app.db.store import get_connection, query, query_one


class PriceLockRepository:
    """Persist and query price-lock rules and items."""

    @staticmethod
    def _generate_rule_code(cursor: Any, prefix: str = "PLCK") -> str:
        import uuid as _uuid
        return f"{prefix}-{_uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def create(data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            code = PriceLockRepository._generate_rule_code(cursor)
            cursor.execute(
                """INSERT INTO PriceLockRule
                   (rule_code, rule_name, salemenu_id, salemenu_name,
                    target_count, start_time, end_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    code,
                    data["rule_name"],
                    data.get("salemenu_id"),
                    data.get("salemenu_name"),
                    data.get("target_count", 0),
                    data.get("start_time"),
                    data.get("end_time"),
                ),
            )
            rule_id = cursor.lastrowid
            count = 0
            for item in data.get("items", []):
                cursor.execute(
                    """INSERT INTO PriceLockRuleItem
                       (rule_id, veg_name, locked_price)
                       VALUES (?, ?, ?)""",
                    (rule_id, item["veg_name"], item.get("locked_price", 0)),
                )
                count += 1
            cursor.execute(
                "UPDATE PriceLockRule SET category_count = ? WHERE id = ?",
                (count, rule_id),
            )
            conn.commit()
            return rule_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def get_by_id(rule_id: int) -> dict[str, Any] | None:
        return query_one("SELECT * FROM PriceLockRule WHERE id = ?", (rule_id,))

    @staticmethod
    def get_items(rule_id: int) -> list[dict[str, Any]]:
        return query("SELECT * FROM PriceLockRuleItem WHERE rule_id = ?", (rule_id,))

    @staticmethod
    def list_rules(
        *, search: str = "", status: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("(rule_name LIKE ? OR rule_code LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return query(
            f"SELECT * FROM PriceLockRule {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )

    @staticmethod
    def count_rules(*, search: str = "", status: str | None = None) -> int:
        clauses = []
        params: list[Any] = []
        if search:
            clauses.append("(rule_name LIKE ? OR rule_code LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        row = query_one(f"SELECT COUNT(*) AS cnt FROM PriceLockRule {where}", tuple(params))
        return row["cnt"] if row else 0

    @staticmethod
    def update(rule_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            sets = []
            vals: list[Any] = []
            for field in ("rule_name", "start_time", "end_time"):
                if field in data and data[field] is not None:
                    sets.append(f"{field} = ?")
                    vals.append(data[field])
            if not sets:
                return True
            vals.append(rule_id)
            cursor.execute(
                f"UPDATE PriceLockRule SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
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
    def deactivate(rule_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE PriceLockRule SET status = 'inactive', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (rule_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
