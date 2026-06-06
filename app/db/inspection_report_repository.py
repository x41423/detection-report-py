"""Inspection report repository — data access layer."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.db.store import get_connection, query, query_one

logger = logging.getLogger(__name__)


class InspectionReportRepository:
    """Data access for InspectionReport + InspectionReportProduct."""

    # ------------------------------------------------------------------
    # Report No. generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_report_no(cursor: Any) -> str:
        today = date.today().strftime("%Y%m%d")
        cursor.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(report_no, -3) AS INTEGER)), 0) + 1 AS seq "
            "FROM InspectionReport WHERE report_no LIKE ?",
            (f"IRT-{today}-%",),
        )
        row = cursor.fetchone()
        seq = int(row["seq"]) if row else 1
        return f"IRT-{today}-{seq:03d}"

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    @staticmethod
    def create_report(data: dict[str, Any]) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            report_no = InspectionReportRepository._generate_report_no(cursor)

            cursor.execute(
                """INSERT INTO InspectionReport (
                    report_no, name, file_url, test_date, valid_from, valid_until,
                    supplier_id, submit_org, test_org, status, source,
                    pesticide_task_id, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    report_no,
                    data.get("name", ""),
                    data.get("file_url", ""),
                    data.get("test_date", ""),
                    data.get("valid_from", ""),
                    data.get("valid_until", ""),
                    data.get("supplier_id", 0),
                    data.get("submit_org", ""),
                    data.get("test_org", ""),
                    data.get("status", "draft"),
                    data.get("source", "manual"),
                    data.get("pesticide_task_id", 0),
                    data["uploaded_by"],
                ),
            )
            report_id = cursor.lastrowid

            for p in data.get("products", []) or []:
                InspectionReportRepository._add_product(cursor, report_id, p)

            conn.commit()
            return report_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def _add_product(cursor: Any, report_id: int, product_data: dict) -> int:
        cursor.execute(
            """INSERT INTO InspectionReportProduct (report_id, sku_id, product_id, batch)
               VALUES (?, ?, ?, ?)""",
            (
                report_id,
                product_data.get("sku_id", 0),
                product_data.get("product_id", 0),
                product_data.get("batch", ""),
            ),
        )
        return cursor.lastrowid

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    @staticmethod
    def update_report(report_id: int, data: dict[str, Any]) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            sets: list[str] = []
            values: list[Any] = []

            for field in (
                "name", "file_url", "test_date", "valid_from", "valid_until",
                "supplier_id", "submit_org", "test_org", "status",
            ):
                if field in data and data[field] is not None:
                    sets.append(f"{field} = ?")
                    values.append(data[field])

            if not sets:
                return False

            sets.append("updated_at = CURRENT_TIMESTAMP")
            values.append(report_id)
            cursor.execute(
                f"UPDATE InspectionReport SET {', '.join(sets)} WHERE id = ?",
                values,
            )

            # Replace products when provided
            if "products" in data and data["products"] is not None:
                cursor.execute(
                    "DELETE FROM InspectionReportProduct WHERE report_id = ?",
                    (report_id,),
                )
                for p in data["products"]:
                    InspectionReportRepository._add_product(cursor, report_id, p)

            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    @staticmethod
    def list_reports(
        search: str = "",
        status: str = "",
        supplier_id: int = 0,
        test_date_from: str = "",
        test_date_to: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        where_parts: list[str] = []
        params: list[Any] = []

        if search.strip():
            where_parts.append(
                "(ir.name LIKE ? OR ir.report_no LIKE ? OR ir.submit_org LIKE ? OR ir.test_org LIKE ?)"
            )
            like = f"%{search.strip()}%"
            params.extend([like, like, like, like])

        if status.strip():
            where_parts.append("ir.status = ?")
            params.append(status.strip())

        if supplier_id > 0:
            where_parts.append("ir.supplier_id = ?")
            params.append(supplier_id)

        if test_date_from.strip():
            where_parts.append("ir.test_date >= ?")
            params.append(test_date_from.strip())

        if test_date_to.strip():
            where_parts.append("ir.test_date <= ?")
            params.append(test_date_to.strip())

        where = " AND ".join(where_parts) if where_parts else "1=1"

        sql = f"""
            SELECT ir.*,
                   s.name AS supplier_name,
                   ir.uploaded_by AS uploader_name,
                   (SELECT COUNT(*) FROM InspectionReportProduct WHERE report_id = ir.id) AS product_count
            FROM InspectionReport ir
            LEFT JOIN Supplier s ON ir.supplier_id = s.id
            WHERE {where}
            ORDER BY ir.created_at DESC
            LIMIT ? OFFSET ?
        """
        return query(sql, (*params, limit, offset))

    @staticmethod
    def count_reports(
        search: str = "",
        status: str = "",
        supplier_id: int = 0,
        test_date_from: str = "",
        test_date_to: str = "",
    ) -> int:
        where_parts: list[str] = []
        params: list[Any] = []

        if search.strip():
            where_parts.append(
                "(ir.name LIKE ? OR ir.report_no LIKE ? OR ir.submit_org LIKE ? OR ir.test_org LIKE ?)"
            )
            like = f"%{search.strip()}%"
            params.extend([like, like, like, like])

        if status.strip():
            where_parts.append("ir.status = ?")
            params.append(status.strip())

        if supplier_id > 0:
            where_parts.append("ir.supplier_id = ?")
            params.append(supplier_id)

        if test_date_from.strip():
            where_parts.append("ir.test_date >= ?")
            params.append(test_date_from.strip())

        if test_date_to.strip():
            where_parts.append("ir.test_date <= ?")
            params.append(test_date_to.strip())

        where = " AND ".join(where_parts) if where_parts else "1=1"
        row = query_one(f"SELECT COUNT(*) AS cnt FROM InspectionReport ir WHERE {where}", params)
        return int(row["cnt"]) if row else 0

    # ------------------------------------------------------------------
    # GET (detail)
    # ------------------------------------------------------------------

    @staticmethod
    def get_report(report_id: int) -> dict | None:
        row = query_one(
            """SELECT ir.*,
                      s.name AS supplier_name,
                      ir.uploaded_by AS uploader_name,
                      (SELECT COUNT(*) FROM InspectionReportProduct WHERE report_id = ir.id) AS product_count
               FROM InspectionReport ir
               LEFT JOIN Supplier s ON ir.supplier_id = s.id
               WHERE ir.id = ?""",
            (report_id,),
        )
        if row is None:
            return None

        products = query(
            """SELECT irp.*, p.name AS product_name, p.code AS product_code,
                      sku.name AS sku_name
               FROM InspectionReportProduct irp
               LEFT JOIN Product p ON irp.product_id = p.id
               LEFT JOIN ProductSku sku ON irp.sku_id = sku.id
               WHERE irp.report_id = ?
               ORDER BY irp.id""",
            (report_id,),
        )
        row["products"] = products or []
        return row

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    @staticmethod
    def delete_report(report_id: int) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM InspectionReportProduct WHERE report_id = ?", (report_id,))
            cursor.execute("DELETE FROM InspectionReport WHERE id = ?", (report_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
