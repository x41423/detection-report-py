"""Aggregated read-only queries for Dashboard."""
from __future__ import annotations

from typing import Any

from app.db.store import query, query_one


class DashboardRepository:
    """Cross-table aggregation for data cockpit."""

    @staticmethod
    def get_overview(current_month: str) -> dict[str, Any]:
        # Total & active suppliers
        sup = query_one("SELECT COUNT(*) AS total FROM Supplier")
        act = query_one("SELECT COUNT(*) AS total FROM Supplier WHERE status = 'active'")

        # Purchase this month (confirmed)
        pur = query_one(
            """SELECT COALESCE(SUM(pi.amount), 0) AS total
               FROM PurchaseInRecord r
               JOIN PurchaseInItem pi ON pi.record_id = r.id
               WHERE r.status = 'confirmed'
                 AND r.inbound_date >= ? || '-01'
                 AND r.inbound_date <= ? || '-31'""",
            (current_month, current_month),
        )

        # Orders this month
        ord_ = query_one(
            """SELECT COALESCE(SUM(order_amount), 0) AS total
               FROM OrderRecord
               WHERE order_date >= ? || '-01'
                 AND order_date <= ? || '-31'""",
            (current_month, current_month),
        )

        # Pending settlements
        stl = query_one("SELECT COUNT(*) AS total FROM SupplierSettlement WHERE status = 'pending'")

        # Low stock items (<= 10)
        low = query_one(
            """SELECT COUNT(*) AS total FROM (
                SELECT 1
                FROM InventoryTransaction tx
                JOIN Unit u ON u.id = tx.unit_id
                GROUP BY tx.normalized_name
                HAVING COALESCE(SUM(CASE WHEN tx.direction = 'IN'  THEN tx.quantity_delta ELSE 0 END), 0)
                     - COALESCE(SUM(CASE WHEN tx.direction = 'OUT' THEN tx.quantity_delta ELSE 0 END), 0) <= 10
            )""",
        )

        return {
            "total_suppliers": sup["total"] if sup else 0,
            "active_suppliers": act["total"] if act else 0,
            "purchase_this_month": float(pur["total"]) if pur else 0,
            "orders_this_month": float(ord_["total"]) if ord_ else 0,
            "pending_settlements": stl["total"] if stl else 0,
            "low_stock_items": low["total"] if low else 0,
        }

    @staticmethod
    def get_purchase_trend(months: int = 6) -> list[dict[str, Any]]:
        return query(
            """SELECT
                substr(r.inbound_date, 1, 7) AS period,
                COALESCE(SUM(pi.amount), 0) AS amount,
                COUNT(DISTINCT r.id) AS count
               FROM PurchaseInRecord r
               JOIN PurchaseInItem pi ON pi.record_id = r.id
               WHERE r.status = 'confirmed'
               GROUP BY period
               ORDER BY period DESC
               LIMIT ?""",
            (months,),
        )

    @staticmethod
    def get_order_trend(months: int = 6) -> list[dict[str, Any]]:
        return query(
            """SELECT
                substr(order_date, 1, 7) AS period,
                COALESCE(SUM(order_amount), 0) AS amount,
                COUNT(*) AS count
               FROM OrderRecord
               GROUP BY period
               ORDER BY period DESC
               LIMIT ?""",
            (months,),
        )

    @staticmethod
    def get_top_suppliers(limit: int = 5) -> list[dict[str, Any]]:
        return query(
            """SELECT
                r.supplier_id,
                s.name AS supplier_name,
                COALESCE(SUM(pi.amount), 0) AS total_amount,
                COUNT(DISTINCT r.id) AS order_count
               FROM PurchaseInRecord r
               JOIN PurchaseInItem pi ON pi.record_id = r.id
               JOIN Supplier s ON s.id = r.supplier_id
               WHERE r.status = 'confirmed'
               GROUP BY r.supplier_id
               ORDER BY total_amount DESC
               LIMIT ?""",
            (limit,),
        )
