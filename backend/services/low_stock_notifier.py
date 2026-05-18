import logging
from backend.services.config_service import get_config

logger = logging.getLogger(__name__)


class LowStockNotifier:
    """Check inventory balances against low-stock threshold."""

    def __init__(self, threshold: int | None = None):
        if threshold is None:
            threshold = get_config().get("inventory_low_stock_threshold", 3)
        self.threshold = threshold

    def _query_balances(self) -> list[dict]:
        from app.db.inventory_repository import InventoryRepository

        repo = InventoryRepository()
        try:
            return repo.list_balances(limit=1000)
        except Exception as e:
            logger.error(f"Failed to query balances: {e}")
            return []

    def check(self) -> list[dict]:
        balances = self._query_balances()
        alerts = []
        for item in balances:
            balance = item.get("balance", 0)
            if isinstance(balance, (int, float)) and balance <= self.threshold:
                alerts.append({
                    "item_name": item.get("item_name", item.get("veg_name", "")),
                    "balance": balance,
                    "unit": item.get("unit", ""),
                    "threshold": self.threshold,
                })
        if alerts:
            logger.warning(
                f"Low stock alert: {len(alerts)} items below threshold {self.threshold}"
            )
        return alerts
