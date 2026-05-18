from __future__ import annotations

import os

from app.db.weekly_quote_repository import WeeklyQuoteRepository, week_bounds
from app.utils.weekly_quote_summary import (
    BUILTIN_SUPPLIERS,
    export_weekly_quote_summary,
    import_weekly_quote_batch,
    preview_weekly_quote_summary,
)

EXCEL_SHEET_INVALID_CHARS = set("[]:*?/\\")


class WeeklyQuoteSummaryService:

    def __init__(self):
        self.repo = WeeklyQuoteRepository()

    def get_options(self) -> dict:
        return {
            "success": True,
            "suppliers": self._supplier_configs(),
            "measure_units": self.repo.get_measure_unit_options(),
        }

    def create_supplier(
        self,
        name: str,
        weekly_batch_limit: int,
        summary_rule: str,
    ) -> dict:
        normalized_name = self._validate_supplier_name(name)
        if self.repo.get_supplier_config_by_name(normalized_name):
            raise ValueError(f"报价单位已存在: {normalized_name}")
        if summary_rule not in {"highest", "average"}:
            raise ValueError("汇总规则只能是 highest 或 average")
        if weekly_batch_limit < 1 or weekly_batch_limit > 7:
            raise ValueError("周记录上限必须在 1 到 7 之间")
        supplier = self.repo.upsert_supplier_config(
            normalized_name,
            weekly_batch_limit=weekly_batch_limit,
            summary_rule=summary_rule,
            is_builtin=False,
        )
        return {"success": True, "message": "报价单位已添加", "supplier": supplier}

    def create_measure_unit(self, name: str) -> dict:
        normalized_name = self._validate_measure_unit_name(name)
        if self.repo.get_measure_unit_option_by_name(normalized_name):
            raise ValueError(f"计量单位已存在: {normalized_name}")
        measure_unit = self.repo.upsert_measure_unit_option(normalized_name)
        return {"success": True, "message": "计量单位已添加", "measure_unit": measure_unit}

    def save_manual_batch(self, supplier: str, quote_date: str, entries: list[dict],
                          source_label: str = "手动录入") -> dict:
        supplier_configs = self._supplier_configs()
        weekly_batches = [
            batch
            for batch in self.repo.list_weekly_batches(supplier, quote_date)
            if batch["quote_date"] != quote_date
        ]
        preview_weekly_quote_summary(
            [
                {
                    "supplier": batch["supplier"],
                    "quote_date": batch["quote_date"],
                    "entries": batch["entries"],
                }
                for batch in weekly_batches
            ]
            + [
                {
                    "supplier": supplier,
                    "quote_date": quote_date,
                    "entries": entries,
                }
            ],
            supplier_configs=supplier_configs,
        )
        saved = self.repo.save_batch(
            supplier=supplier,
            quote_date=quote_date,
            entries=entries,
            source_label=source_label,
        )
        self.repo.ensure_measure_unit_options([entry.get("unit", "") for entry in entries])
        return {"success": True, "batch": saved}

    def list_saved_batches(self, supplier: str) -> dict:
        batches = self.repo.list_batches(supplier)
        return {"success": True, "batches": batches}

    def delete_batch(self, supplier: str, quote_date: str) -> dict:
        ok = self.repo.delete_batch(supplier, quote_date)
        return {"success": ok}

    def get_weekly_summary(self, supplier: str, date_str: str) -> dict:
        supplier_configs = self._supplier_configs()
        batches = self.repo.list_weekly_batches(supplier, date_str)
        if not batches:
            return {
                "success": True,
                "supplier": supplier,
                "batch_count": 0,
                "entry_count": 0,
                "summary_items": [],
                "total_summary_items": 0,
            }

        summary = preview_weekly_quote_summary(
            [
                {
                    "supplier": batch["supplier"],
                    "quote_date": batch["quote_date"],
                    "entries": batch["entries"],
                }
                for batch in batches
            ],
            supplier_configs=supplier_configs,
        )
        unit_summary = next(
            (item for item in summary["unit_summaries"] if item["supplier"] == supplier),
            {"batch_count": 0, "entry_count": 0, "summary_items": []},
        )
        items = unit_summary["summary_items"]
        return {
            "success": True,
            "supplier": supplier,
            "batch_count": unit_summary["batch_count"],
            "entry_count": unit_summary["entry_count"],
            "summary_items": items,
            "total_summary_items": len(items),
        }

    def get_week_overview(self, date_str: str) -> dict:
        supplier_configs = self._supplier_configs()
        supplier_names = [config["name"] for config in supplier_configs]
        supplier_config_by_name = {config["name"]: config for config in supplier_configs}
        week_start, week_end = week_bounds(date_str)
        batches = self.repo.list_weekly_batches_for_suppliers(supplier_names, date_str)
        summary_by_supplier = {
            supplier: {
                "supplier": supplier,
                "batch_count": 0,
                "entry_count": 0,
                "summary_items": [],
            }
            for supplier in supplier_names
        }
        issue_messages: list[str] = []
        total_batches = len(batches)
        total_entries = sum(int(batch.get("entry_count") or len(batch.get("entries") or [])) for batch in batches)
        total_summary_items = 0

        if batches:
            summary = preview_weekly_quote_summary(
                [
                    {
                        "supplier": batch["supplier"],
                    "quote_date": batch["quote_date"],
                    "entries": batch["entries"],
                }
                for batch in batches
            ],
            supplier_configs=supplier_configs,
        )
            summary_by_supplier = {
                item["supplier"]: item
                for item in summary["unit_summaries"]
            }
            total_batches = summary["total_batches"]
            total_entries = summary["total_entries"]
            total_summary_items = summary["total_summary_items"]
            issue_messages = summary["issue_messages"]

        batches_by_supplier = {supplier: [] for supplier in supplier_names}
        for batch in batches:
            batches_by_supplier[batch["supplier"]].append(batch)

        supplier_payloads = []
        for supplier in supplier_names:
            summary = summary_by_supplier[supplier]
            config = supplier_config_by_name[supplier]
            supplier_payloads.append(
                {
                    "supplier": supplier,
                    "limit": int(config["weekly_batch_limit"]),
                    "summary_rule": config["summary_rule"],
                    "batches": batches_by_supplier[supplier],
                    "batch_count": summary["batch_count"],
                    "entry_count": summary["entry_count"],
                    "summary_items": summary["summary_items"],
                }
            )

        return {
            "success": True,
            "week_start": week_start,
            "week_end": week_end,
            "suppliers": supplier_payloads,
            "total_batches": total_batches,
            "total_entries": total_entries,
            "total_summary_items": total_summary_items,
            "issue_messages": issue_messages,
        }

    def get_all_suppliers(self) -> dict:
        builtin = list(BUILTIN_SUPPLIERS)
        dynamic = [item["name"] for item in self._supplier_configs()]
        all_suppliers = sorted(set(builtin + dynamic))
        return {"success": True, "suppliers": all_suppliers}

    def import_batch(self, supplier: str, quote_date: str, source_path: str) -> dict:
        supplier_configs = self._supplier_configs()
        batch = import_weekly_quote_batch(
            source_path=source_path,
            supplier=supplier,
            quote_date=quote_date,
            supplier_configs=supplier_configs,
        )
        return {
            "success": True,
            "message": f"{batch['supplier']} {batch['quote_date']} 导入成功，共 {len(batch['entries'])} 条记录",
            "batch": batch,
        }

    def preview(self, batches: list[dict]) -> dict:
        summary = preview_weekly_quote_summary(batches, supplier_configs=self._supplier_configs())
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

        supplier_configs = self._supplier_configs()
        result = export_weekly_quote_summary(
            workbook_path=workbook_path,
            batches=batches,
            supplier_configs=supplier_configs,
        )
        return {
            "success": True,
            "message": (
                f"新报价总结已输出为 {os.path.basename(result['workbook_path'])}，"
                f"共更新 {len(supplier_configs)} 个单位 sheet"
            ),
            "workbook_path": result["workbook_path"],
            "sheet_names": result["sheet_names"],
            "unit_summaries": result["unit_summaries"],
            "total_batches": result["total_batches"],
            "total_entries": result["total_entries"],
            "total_summary_items": result["total_summary_items"],
        }

    def export_week(self, workbook_path: str, date_str: str) -> dict:
        supplier_configs = self._supplier_configs()
        batches = self.repo.list_weekly_batches_for_suppliers(
            [config["name"] for config in supplier_configs],
            date_str,
        )
        return self.export(
            workbook_path=workbook_path,
            batches=[
                {
                    "supplier": batch["supplier"],
                    "quote_date": batch["quote_date"],
                    "entries": batch["entries"],
                }
                for batch in batches
            ],
        )

    def _supplier_configs(self) -> list[dict]:
        return self.repo.get_supplier_configs()

    def _validate_supplier_name(self, name: str) -> str:
        normalized = str(name or "").strip()
        if not normalized:
            raise ValueError("报价单位名称不能为空")
        if len(normalized) > 31:
            raise ValueError("报价单位名称不能超过 31 个字符")
        invalid_chars = sorted(char for char in EXCEL_SHEET_INVALID_CHARS if char in normalized)
        if invalid_chars:
            raise ValueError(f"报价单位名称不能包含这些字符: {''.join(invalid_chars)}")
        return normalized

    def _validate_measure_unit_name(self, name: str) -> str:
        normalized = str(name or "").strip()
        if not normalized:
            raise ValueError("计量单位名称不能为空")
        if len(normalized) > 64:
            raise ValueError("计量单位名称不能超过 64 个字符")
        return normalized
