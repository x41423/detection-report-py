"""Lightweight single-table CRUD helpers for simple management modules.

These are plain functions — each Repository class stays @staticmethod
and calls into these helpers when its table fits the single-table pattern.

For complex modules (master-detail, N:M, JOIN-heavy queries), write
custom SQL in the Repository class as before.
"""

from __future__ import annotations

import logging

from app.db.store import get_connection, query

logger = logging.getLogger(__name__)


def _default_for(column_name: str) -> str | int | float:
    if column_name.endswith("_id") or column_name in ("sort_order",):
        return 0
    return ""


def simple_create(
    table: str,
    columns: tuple[str, ...],
    data: dict,
) -> int:
    """Single-table INSERT.  Returns lastrowid."""
    cols = ", ".join(columns)
    ph = ", ".join(["?"] * len(columns))
    values = [data.get(c, _default_for(c)) for c in columns]
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({ph})",
            values,
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def simple_update(
    table: str,
    pk: int,
    columns: tuple[str, ...],
    data: dict,
) -> bool:
    """Single-table UPDATE by id.  Returns True when a row was changed."""
    sets = [f"{c} = ?" for c in columns]
    values = [data.get(c, _default_for(c)) for c in columns] + [pk]
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def simple_delete(table: str, pk: int) -> bool:
    """Single-table DELETE by id.  Returns True when a row was removed."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (pk,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def simple_list(
    table: str,
    limit: int = 50,
    offset: int = 0,
    where: str = "",
    params: tuple = (),
    order: str = "id DESC",
) -> list[dict]:
    """Single-table SELECT with optional WHERE and pagination."""
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    sql += f" ORDER BY {order} LIMIT ? OFFSET ?"
    return query(sql, (*params, limit, offset))


def simple_count(
    table: str,
    where: str = "",
    params: tuple = (),
) -> int:
    """Count rows matching optional WHERE clause."""
    sql = f"SELECT COUNT(*) AS cnt FROM {table}"
    if where:
        sql += f" WHERE {where}"
    row = query(sql, params)
    return int(row[0]["cnt"]) if row else 0
