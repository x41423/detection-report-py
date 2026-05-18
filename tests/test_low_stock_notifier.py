from unittest.mock import patch, MagicMock
from backend.services.low_stock_notifier import LowStockNotifier


def test_check_low_stock():
    mock_data = [
        {"item_name": "菠菜", "balance": 2.0, "unit": "斤"},
        {"item_name": "大白菜", "balance": 10.0, "unit": "斤"},
        {"item_name": "白萝卜", "balance": 3.0, "unit": "斤"},
    ]

    with patch.object(LowStockNotifier, "_query_balances", return_value=mock_data):
        notifier = LowStockNotifier(threshold=3)
        alerts = notifier.check()
        assert len(alerts) == 2
        assert alerts[0]["item_name"] == "菠菜"
        assert alerts[1]["item_name"] == "白萝卜"


def test_check_no_alerts():
    mock_data = [
        {"item_name": "菠菜", "balance": 10.0, "unit": "斤"},
    ]
    with patch.object(LowStockNotifier, "_query_balances", return_value=mock_data):
        notifier = LowStockNotifier(threshold=3)
        alerts = notifier.check()
        assert len(alerts) == 0
