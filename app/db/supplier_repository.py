"""Supplier repository — 真实供应商（上游供货商）数据访问."""

from __future__ import annotations

from typing import Any

from app.db.store import get_connection


class SupplierRepository:
    TABLE = "Supplier"

    @staticmethod
    def list(*, search: str = "", status: str = "", limit: int = 20, offset: int = 0) -> dict:
        conn = get_connection()
        where = []
        params: list[Any] = []
        if search:
            where.append("(supplier_code LIKE ? OR name LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if status:
            where.append("status = ?")
            params.append(status)
        where_clause = ("WHERE " + " AND ".join(where)) if where else ""
        count_sql = f"SELECT COUNT(*) AS cnt FROM {SupplierRepository.TABLE} {where_clause}"
        row = conn.execute(count_sql, params).fetchone()
        total = row["cnt"] if row else 0
        sql = f"SELECT * FROM {SupplierRepository.TABLE} {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        rows = [dict(r) for r in conn.execute(sql, params + [limit, offset]).fetchall()]
        return {"items": rows, "total": total}

    @staticmethod
    def get_by_id(sid: int) -> dict | None:
        conn = get_connection()
        row = conn.execute(f"SELECT * FROM {SupplierRepository.TABLE} WHERE id=?", (sid,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(data: dict) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cols = [k for k in data if k != "id"]
        placeholders = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO {SupplierRepository.TABLE} ({', '.join(cols)}) VALUES ({placeholders})"
        cursor.execute(sql, [data[c] for c in cols])
        conn.commit()
        return cursor.lastrowid or 0

    @staticmethod
    def update(sid: int, data: dict) -> bool:
        if not data:
            return False
        conn = get_connection()
        sets = ", ".join(f"{k}=?" for k in data)
        values = list(data.values()) + [sid]
        sql = f"UPDATE {SupplierRepository.TABLE} SET {sets}, updated_at=NOW() WHERE id=?"
        conn.execute(sql, values)
        conn.commit()
        return True

    @staticmethod
    def delete(sid: int) -> bool:
        conn = get_connection()
        conn.execute(f"UPDATE {SupplierRepository.TABLE} SET status='inactive', updated_at=NOW() WHERE id=?", (sid,))
        conn.commit()
        return True
