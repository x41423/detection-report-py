import json
import logging
import os
import re
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
            sheet_data = sheet.get("sheet", {})
            seen = set()
            for item in sheet_data.get("items", []):
                name = item.get("normalized_name") or item.get("raw_name", "")
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
                yesterday_data = yesterday_sheet.get("sheet", {})
                for item in yesterday_data.get("items", []):
                    name = item.get("normalized_name") or item.get("raw_name", "")
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
            # Ensure output directory exists
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            process_documents(
                big_template, small_template, rates,
                target_date, str(out_dir), inspector_name
            )
            self._rename_output_files(out_dir, target_date)
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

        mimo_analysis = None
        if os.getenv("MIMO_ENABLED", "").strip().lower() in ("1", "true", "yes"):
            try:
                from backend.services.mimo_service import MimoService
                ms = MimoService()
                reply = ms.analyze_rates(all_veggies, {"rates": rates})
                if reply:
                    mimo_analysis = reply
                    logger.info("MiMo analysis appended to detection result")
            except Exception:
                logger.debug("MiMo analysis skipped")

        return {
            "success": True,
            "output_paths": archive_result,
            "pdf_files": pdf_files,
            "low_stock_alerts": alerts,
            "mimo_analysis": mimo_analysis,
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

    def _rename_output_files(self, out_dir: Path, date_str: str) -> None:
        """Rename template-named outputs to date-based detection report names."""
        d = self._parse_date(date_str)
        mappings = [
            ("big-template.docx", f"农残检测记录表{d.year}.{d.month:02d}.{d.day:02d}.docx"),
            ("big-template-0.docx", f"农残检测记录表{d.year}.{d.month:02d}.{d.day:02d}.docx"),
            ("small-template.docx", f"单位农残记录表{d.month}.{d.day}.docx"),
        ]
        for old_name, new_name in mappings:
            old_path = out_dir / old_name
            new_path = out_dir / new_name
            if old_path.exists():
                try:
                    new_path.unlink(missing_ok=True)
                    old_path.rename(new_path)
                    logger.info(f"Renamed {old_name} -> {new_name}")
                except Exception as e:
                    logger.warning(f"Failed to rename {old_name}: {e}")

        # Also rename overflow big pages (-1, -2, ...)
        for f in out_dir.glob("big-template-*.docx"):
            try:
                match = re.match(r"big-template-(\d+).docx", f.name)
                if match:
                    idx = int(match.group(1))
                    new_name = f"农残检测记录表{d.year}.{d.month:02d}.{d.day:02d}-{idx}.docx"
                    new_path = out_dir / new_name
                    new_path.unlink(missing_ok=True)
                    f.rename(new_path)
                    logger.info(f"Renamed {f.name} -> {new_name}")
            except Exception as e:
                logger.warning(f"Failed to rename overflow page {f.name}: {e}")
