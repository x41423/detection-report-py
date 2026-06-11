"""Product & order analytics — aggregated read-only queries."""

from __future__ import annotations

from app.db.store import query


class ProductAnalysisRepository:

    # ── Product sales ────────────────────────────────────────────────

    @staticmethod
    def top_products(date_from: str = "", date_to: str = "", limit: int = 20) -> list[dict]:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND o.order_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND o.order_date <= ?"
            params.append(date_to.strip())
        params.append(limit)
        return query(
            f"""SELECT oi.product_name, SUM(oi.amount) AS total_amount,
                       SUM(oi.quantity) AS total_qty, COUNT(DISTINCT o.id) AS order_count
                FROM OrderItem oi JOIN OrderRecord o ON oi.order_id = o.id
                WHERE {where} GROUP BY oi.product_name
                ORDER BY total_amount DESC LIMIT ?""",
            params,
        )

    @staticmethod
    def by_category(date_from: str = "", date_to: str = "") -> list[dict]:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND o.order_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND o.order_date <= ?"
            params.append(date_to.strip())
        return query(
            f"""SELECT COALESCE(oi.category, '未分类') AS category,
                       SUM(oi.amount) AS total_amount, COUNT(*) AS item_count
                FROM OrderItem oi JOIN OrderRecord o ON oi.order_id = o.id
                WHERE {where} GROUP BY oi.category ORDER BY total_amount DESC""",
            params,
        )

    @staticmethod
    def summary(date_from: str = "", date_to: str = "") -> dict:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND order_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND order_date <= ?"
            params.append(date_to.strip())
        row = query(
            f"""SELECT COUNT(*) AS order_count,
                       COALESCE(SUM(order_amount), 0) AS total_amount,
                       COALESCE(SUM(sales_amount_incl_freight), 0) AS total_sales,
                       COUNT(DISTINCT merchant_name) AS merchant_count
                FROM OrderRecord WHERE {where}""",
            params,
        )
        return row[0] if row else {"order_count": 0, "total_amount": 0, "total_sales": 0, "merchant_count": 0}

    # ── Order list ───────────────────────────────────────────────────

    @staticmethod
    def orders_by_date(date_from: str = "", date_to: str = "", limit: int = 200, offset: int = 0) -> list[dict]:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND order_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND order_date <= ?"
            params.append(date_to.strip())
        params.extend([limit, offset])
        return query(
            f"""SELECT order_no, order_date, merchant_name, order_amount,
                       sales_amount_incl_freight, freight, discount_amount,
                       order_status, payment_status
                FROM OrderRecord WHERE {where}
                ORDER BY order_date DESC, id DESC LIMIT ? OFFSET ?""",
            params,
        )

    @staticmethod
    def orders_count(date_from: str = "", date_to: str = "") -> int:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND order_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND order_date <= ?"
            params.append(date_to.strip())
        row = query(f"SELECT COUNT(*) AS cnt FROM OrderRecord WHERE {where}", params)
        return int(row[0]["cnt"]) if row else 0

    # ── Customer analysis ─────────────────────────────────────────────

    @staticmethod
    def customer_ranking(date_from: str = "", date_to: str = "", limit: int = 30) -> list[dict]:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND order_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND order_date <= ?"
            params.append(date_to.strip())
        params.append(limit)
        return query(
            f"""SELECT merchant_name, COUNT(*) AS order_count,
                       SUM(order_amount) AS total_amount,
                       ROUND(AVG(order_amount), 2) AS avg_amount
                FROM OrderRecord WHERE {where}
                GROUP BY merchant_name ORDER BY total_amount DESC LIMIT ?""",
            params,
        )

    @staticmethod
    def customer_summary(date_from: str = "", date_to: str = "") -> dict:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND order_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND order_date <= ?"
            params.append(date_to.strip())
        row = query(
            f"""SELECT COUNT(DISTINCT merchant_name) AS customer_count,
                       COUNT(*) AS order_count,
                       COALESCE(SUM(order_amount), 0) AS total_amount
                FROM OrderRecord WHERE {where}""",
            params,
        )
        return row[0] if row else {"customer_count": 0, "order_count": 0, "total_amount": 0}

    # ── Inventory summary ─────────────────────────────────────────────

    @staticmethod
    def inventory_summary(date_from: str = "", date_to: str = "") -> dict:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND business_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND business_date <= ?"
            params.append(date_to.strip())
        row = query(
            f"""SELECT COUNT(*) AS total_txns,
                       SUM(CASE WHEN direction='in' THEN ABS(quantity_delta) ELSE 0 END) AS total_in,
                       SUM(CASE WHEN direction='out' THEN ABS(quantity_delta) ELSE 0 END) AS total_out
                FROM InventoryTransaction WHERE {where}""",
            params,
        )
        return row[0] if row else {"total_txns": 0, "total_in": 0, "total_out": 0}

    @staticmethod
    def inventory_by_source(date_from: str = "", date_to: str = "") -> list[dict]:
        where = "1=1"
        params: list = []
        if date_from.strip():
            where += " AND business_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND business_date <= ?"
            params.append(date_to.strip())
        return query(
            f"""SELECT source_type, direction, COUNT(*) AS txn_count,
                       SUM(ABS(quantity_delta)) AS total_qty
                FROM InventoryTransaction WHERE {where}
                GROUP BY source_type, direction ORDER BY txn_count DESC""",
            params,
        )

    # ── Payables (P2.6) ───────────────────────────────────────────────

    @staticmethod
    def payables_by_supplier(supplier_id: int = 0) -> list[dict]:
        where = "1=1"
        params: list = []
        if supplier_id > 0:
            where += " AND s.id = ?"
            params.append(supplier_id)
        return query(
            f"""SELECT s.name AS supplier_name, ss.settlement_period,
                       ss.payable_amount, ss.paid_amount, ss.balance_amount,
                       ss.status, ss.reconciliation_status
                FROM MerchantSettlement ss
                JOIN Merchant s ON ss.supplier_id = s.id
                WHERE {where} ORDER BY ss.settlement_period DESC""",
            params,
        )

    # ── Inactive merchants (P2.11) ────────────────────────────────────

    @staticmethod
    def inactive_merchants(days: int = 7) -> list[dict]:
        return query(
            """SELECT merchant_name, MAX(order_date) AS last_order,
                      COUNT(*) AS total_orders,
                      SUM(order_amount) AS total_amount
               FROM OrderRecord
               GROUP BY merchant_name
               HAVING MAX(order_date) < DATE_SUB(CURDATE(), INTERVAL ? DAY)
               ORDER BY last_order DESC""",
            (days,),
        )

    # ── Product ledger (P3.4) ──────────────────────────────────────────

    @staticmethod
    def product_ledger(product_id: int = 0, date_from: str = "", date_to: str = "",
                       limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        where = "1=1"
        params: list = []
        if product_id > 0:
            where += " AND it.product_id = ?"
            params.append(product_id)
        if date_from.strip():
            where += " AND it.business_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND it.business_date <= ?"
            params.append(date_to.strip())
        cnt = query(f"SELECT COUNT(*) AS n FROM InventoryTransaction it WHERE {where}", params)
        total = cnt[0]["n"] if cnt else 0
        params += [limit, offset]
        rows = query(
            f"""SELECT it.id, it.display_name, it.direction, it.quantity_delta,
                       it.business_date, it.source_type, it.unit_name,
                       it.product_id, it.note, it.created_at
                FROM InventoryTransaction it
                WHERE {where}
                ORDER BY it.business_date DESC, it.id DESC
                LIMIT ? OFFSET ?""",
            params,
        )
        return rows, total

    @staticmethod
    def product_ledger_summary(product_id: int = 0, date_from: str = "", date_to: str = "") -> dict:
        where = "1=1"
        params: list = []
        if product_id > 0:
            where += " AND it.product_id = ?"
            params.append(product_id)
        if date_from.strip():
            where += " AND it.business_date >= ?"
            params.append(date_from.strip())
        if date_to.strip():
            where += " AND it.business_date <= ?"
            params.append(date_to.strip())
        rows = query(
            f"""SELECT it.direction, SUM(it.quantity_delta) AS total_qty
                FROM InventoryTransaction it
                WHERE {where} GROUP BY it.direction""",
            params,
        )
        summary = {"in_qty": 0, "out_qty": 0, "net_qty": 0, "transaction_count": 0}
        for r in rows:
            if r["direction"] == "in":
                summary["in_qty"] = r["total_qty"] or 0
            else:
                summary["out_qty"] = r["total_qty"] or 0
        summary["net_qty"] = summary["in_qty"] - abs(summary["out_qty"])
        cnt = query(f"SELECT COUNT(*) AS n FROM InventoryTransaction it WHERE {where}", params)
        summary["transaction_count"] = cnt[0]["n"] if cnt else 0
        return summary
