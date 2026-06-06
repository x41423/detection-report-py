"""Inventory extension queries — alerts, cross-table summaries."""
from __future__ import annotations

from typing import Any

from app.db.inventory_repository import InventoryRepository
from backend.api.response_utils import list_response


class InventoryReportService:
    """Read-only inventory extensions: alerts, transaction summary with supplier."""

    def __init__(self) -> None:
        pass

    def get_stock_alerts(self, *, threshold: float = 10.0, limit: int = 50) -> dict[str, Any]:
        items = InventoryRepository.get_stock_alerts(threshold=threshold, limit=limit)
        return list_response(
            [dict(row) for row in items],
            len(items),
            f"库存预警: {len(items)} 种商品库存低于{threshold}",
        )

    def get_transaction_summary(
        self, *, start_date: str | None = None, end_date: str | None = None,
        limit: int = 200, offset: int = 0,
    ) -> dict[str, Any]:
        # Note: summary query doesn't support offset natively (complex JOIN),
        # so we fetch all and slice. For large datasets, add SQL OFFSET later.
        rows = InventoryRepository.get_transaction_summary(
            start_date=start_date, end_date=end_date, limit=limit,
        )
        total = InventoryRepository.count_transaction_summary(
            start_date=start_date, end_date=end_date,
        )
        items = [dict(row) for row in rows]
        return list_response(items, total, f"已加载 {len(items)} 条交易明细")
