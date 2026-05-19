from datetime import date
from unittest.mock import patch, MagicMock
from backend.services.smart_detection_service import SmartDetectionService


def test_recommend_returns_structure():
    with patch("backend.services.daily_intake_service.DailyIntakeService") as mock_di:

        mock_di_instance = MagicMock()
        mock_di.return_value = mock_di_instance
        mock_di_instance.get_sheet.return_value = {
            "success": True,
            "sheet": {
                "items": [
                    {"raw_name": "大白菜", "normalized_name": "大白菜"},
                    {"raw_name": "黄瓜", "normalized_name": "黄瓜"},
                ]
            }
        }

        svc = SmartDetectionService()
        result = svc.recommend(date(2026, 5, 18))

        assert "today_intake" in result
        assert "yesterday_inventory" in result
        assert len(result["today_intake"]) == 2


def test_execute_returns_result():
    with patch("backend.services.smart_detection_service.DataGeneratorService") as mock_gen, \
         patch("backend.services.smart_detection_service.process_documents") as mock_proc, \
         patch("backend.services.smart_detection_service.OutputArchiver") as mock_arch, \
         patch("backend.services.smart_detection_service.LowStockNotifier") as mock_notif:

        mock_gen_instance = MagicMock()
        mock_gen.return_value = mock_gen_instance
        mock_gen_instance.generate_rates.return_value = [
            {"variety": "大白菜", "rate": "5.044%"}
        ]

        mock_notif_instance = MagicMock()
        mock_notif.return_value = mock_notif_instance
        mock_notif_instance.check.return_value = []

        svc = SmartDetectionService()
        result = svc.execute({
            "selected_varieties": ["大白菜"],
            "date": "2026-05-18",
            "big_template": "/fake/big.docx",
            "small_template": "/fake/small.docx",
            "output_dir": "/fake/output",
            "inspector_name": "测试员",
        })

        assert result["success"] is True
        assert "summary" in result
