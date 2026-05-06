from __future__ import annotations

import os

from app.utils.weekly_quote_summary import (
    SUPPLIERS,
    export_weekly_quote_summary,
    import_weekly_quote_batch,
    preview_weekly_quote_summary,
)


class WeeklyQuoteSummaryService:
    def import_batch(self, supplier: str, quote_date: str, source_path: str) -> dict:
        batch = import_weekly_quote_batch(
            source_path=source_path,
            supplier=supplier,
            quote_date=quote_date,
        )
        return {
            "success": True,
            "message": f"{batch['supplier']} {batch['quote_date']} 导入成功，共 {len(batch['entries'])} 条记录",
            "batch": batch,
        }

    def preview(self, batches: list[dict]) -> dict:
        summary = preview_weekly_quote_summary(batches)
        return {
            "success": True,
            "message": (
                f"新报价总结预览完成，共 {summary['total_batches']} 个批次，"
                f"{summary['total_entries']} 条原始记录，"
                f"{summary['total_summary_items']} 条汇总记录"
            ),
            "unit_summaries": summary["unit_summaries"],
            "total_batches": summary["total_batches"],
            "total_entries": summary["total_entries"],
            "total_summary_items": summary["total_summary_items"],
            "issue_messages": summary["issue_messages"],
        }

    def export(self, workbook_path: str, batches: list[dict]) -> dict:
        if not workbook_path or not os.path.exists(workbook_path):
            raise FileNotFoundError(f"输出工作簿不存在: {workbook_path}")

        result = export_weekly_quote_summary(workbook_path=workbook_path, batches=batches)
        return {
            "success": True,
            "message": (
                f"新报价总结已输出为 {os.path.basename(result['workbook_path'])}，"
                f"共更新 {len(SUPPLIERS)} 个单位 sheet"
            ),
            "workbook_path": result["workbook_path"],
            "sheet_names": result["sheet_names"],
            "unit_summaries": result["unit_summaries"],
            "total_batches": result["total_batches"],
            "total_entries": result["total_entries"],
            "total_summary_items": result["total_summary_items"],
        }
