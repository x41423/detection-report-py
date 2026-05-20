from unittest.mock import patch, MagicMock
from backend.services.low_stock_notifier import LowStockNotifier


def test_check_low_stock():
    mock_data = [
        {"display_name": "菠菜", "available_quantity": 2.0, "unit_name": "斤"},
        {"display_name": "大白菜", "available_quantity": 10.0, "unit_name": "斤"},
        {"display_name": "白萝卜", "available_quantity": 3.0, "unit_name": "斤"},
    ]

    with patch.object(LowStockNotifier, "_query_balances", return_value=mock_data):
        notifier = LowStockNotifier(threshold=3)
        alerts = notifier.check()
        assert len(alerts) == 2
        assert alerts[0]["item_name"] == "菠菜"
        assert alerts[1]["item_name"] == "白萝卜"


def test_check_no_alerts():
    mock_data = [
        {"display_name": "菠菜", "available_quantity": 10.0, "unit_name": "斤"},
    ]
    with patch.object(LowStockNotifier, "_query_balances", return_value=mock_data):
        notifier = LowStockNotifier(threshold=3)
        alerts = notifier.check()
        assert len(alerts) == 0
