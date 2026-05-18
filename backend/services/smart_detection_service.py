import json
import logging
from datetime import date, timedelta
from pathlib import Path

from backend.services.config_service import get_config
from backend.services.data_gen_service import DataGeneratorService
from backend.services.low_stock_notifier import LowStockNotifier
from backend.services.output_archiver import OutputArchiver
from backend.services.export_service import ExportService
from app.utils.doc_handler import process_documents

logger = logging.getLogger(__name__)


class SmartDetectionService:
    """Orchestrates intelligent pesticide detection workflow — recommend veggies, generate reports."""

    def __init__(self):
        cfg = get_config()
        self._gen = DataGeneratorService(
            high_risk=cfg.get("high_risk", []),
            low_risk=cfg.get("low_risk", []),
            rate_ranges=cfg.get("rate_ranges", {}),
        )
        self.output_root = cfg.get("output_dir", "")

    def recommend(self, target_date: date) -> dict:
        """Recommend vegetables to test based on today's intake and yesterday's untested inventory."""
        result = {
            "today_intake": [],
            "yesterday_inventory": [],
            "missing_dates": [],
        }

        try:
            from backend.services.daily_intake_service import DailyIntakeService
            di_service = DailyIntakeService()
            sheet = di_service.get_sheet(target_date.isoformat())
            seen = set()
            for item in sheet.get("items", []):
                name = item.get("normalized_name") or item.get("veg_name", "")
                if name and name not in seen:
                    seen.add(name)
                    result["today_intake"].append({
                        "name": name,
                        "source": "daily_intake",
                        "category": item.get("category", ""),
                    })
        except Exception as e:
            logger.warning(f"Failed to load daily intake for {target_date}: {e}")

        try:
            yesterday = target_date - timedelta(days=1)
            archiver = OutputArchiver(self.output_root)
            yesterday_reports = archiver.find_report(yesterday, "big")

            if not yesterday_reports:
                from backend.services.daily_intake_service import DailyIntakeService
                di_service = DailyIntakeService()
                yesterday_sheet = di_service.get_sheet(yesterday.isoformat())
                for item in yesterday_sheet.get("items", []):
                    name = item.get("normalized_name") or item.get("veg_name", "")
                    if name and name not in seen:
                        seen.add(name)
                        result["yesterday_inventory"].append({
                            "name": name,
                            "source": "yesterday_inventory",
                            "reason": "昨日未检",
                        })
        except Exception as e:
            logger.warning(f"Failed to check yesterday inventory: {e}")

        return result

    def execute(self, request: dict) -> dict:
        """Execute the full detection pipeline."""
        selected = list(request.get("selected_varieties", []))
        manual = request.get("manual_additions", [])
        all_veggies = selected + manual

        if not all_veggies:
            return {"success": False, "error": "没有选择任何蔬菜"}

        big_template = request.get("big_template", "")
        small_template = request.get("small_template", "")
        target_date = request.get("date", "")
        output_dir = request.get("output_dir", self.output_root)
        inspector_name = request.get("inspector_name", "检测员")
        export_format = request.get("export_format", "docx")

        if not big_template or not small_template:
            return {"success": False, "error": "模板路径未设置"}

        try:
            rates = self._gen.generate_rates(all_veggies)
        except Exception as e:
            return {"success": False, "error": f"抑制率生成失败: {e}"}

        try:
            process_documents(
                big_template, small_template, rates,
                target_date, Path(output_dir), inspector_name
            )
        except Exception as e:
            return {"success": False, "error": f"文档生成失败: {e}"}

        archiver = OutputArchiver(output_dir)
        archive_result = {"archived_count": 0}
        try:
            archive_result = archiver.archive(Path(output_dir), self._parse_date(target_date))
        except Exception as e:
            logger.warning(f"Archive failed: {e}")

        pdf_files = []
        if export_format in ("pdf", "both"):
            try:
                exporter = ExportService()
                export_result = exporter.export_detection_report(
                    target_date,
                    [str(p) for p in Path(output_dir).glob("*.docx")],
                    output_dir,
                    format=export_format
                )
                pdf_files = export_result.get("pdf_files", [])
            except Exception as e:
                logger.warning(f"PDF export failed: {e}")

        alerts = []
        try:
            notifier = LowStockNotifier()
            alerts = notifier.check()
        except Exception as e:
            logger.warning(f"Low stock check failed: {e}")

        return {
            "success": True,
            "output_paths": archive_result,
            "pdf_files": pdf_files,
            "low_stock_alerts": alerts,
            "summary": {
                "total_varieties": len(all_veggies),
                "generated_date": target_date,
                "inspector": inspector_name,
            }
        }

    def _parse_date(self, date_str: str) -> date:
        try:
            return date.fromisoformat(date_str)
        except (ValueError, TypeError):
            return date.today()
