import os

from app.utils.weekly_price_update import preview_weekly_prices, update_weekly_prices
from backend.services.config_service import (
    delete_weekly_price_alias,
    get_weekly_price_aliases,
    upsert_weekly_price_aliases,
)


class WeeklyPriceService:
    def preview(
        self,
        update_path: str,
        reference_path: str,
    ) -> dict:
        self._validate_paths(update_path, reference_path)

        summary = preview_weekly_prices(
            update_path=update_path,
            reference_path=reference_path,
            weekly_price_aliases=get_weekly_price_aliases(),
        )

        suggestion_count = sum(
            1
            for item in summary.get("suggested_matches", [])
            if item.get("candidates")
        )
        message = (
            f"预检查完成，已匹配 {summary.get('matched_count', 0)} 条，"
            f"未匹配 {summary.get('not_matched_count', 0)} 条。"
        )
        if suggestion_count:
            message = f"{message} 其中 {suggestion_count} 个菜名有候选建议。"
        if summary.get("warnings"):
            message = f"{message} {summary['warnings'][0]}"

        return {
            "success": True,
            "message": message,
            "matched_count": summary.get("matched_count", 0),
            "updated_count": summary.get("updated_count", 0),
            "matched_items": summary.get("matched_items", []),
            "not_matched": summary.get("not_matched", []),
            "not_matched_count": summary.get("not_matched_count", 0),
            "not_matched_unique_count": summary.get("not_matched_unique_count", 0),
            "suggested_matches": summary.get("suggested_matches", []),
            "alias_hit_count": summary.get("alias_hit_count", 0),
            "warnings": summary.get("warnings", []),
            "update_start_row": summary.get("update_start_row", 0),
            "reference_start_row": summary.get("reference_start_row", 0),
        }

    def execute(
        self,
        update_path: str,
        reference_path: str,
        output_path: str,
    ) -> dict:
        self._validate_paths(update_path, reference_path)

        target_path = str(output_path or "").strip()
        if not target_path:
            raise ValueError("请先指定输出路径")

        target_dir = os.path.dirname(os.path.abspath(target_path))
        if target_dir and not os.path.isdir(target_dir):
            raise FileNotFoundError(f"输出路径所在目录不存在：{target_dir}")

        summary = update_weekly_prices(
            update_path=update_path,
            reference_path=reference_path,
            output_path=target_path,
            weekly_price_aliases=get_weekly_price_aliases(),
        )

        not_matched_count = summary.get("not_matched_count", 0)
        unique_not_matched_count = summary.get("not_matched_unique_count", 0)
        alias_hit_count = summary.get("alias_hit_count", 0)

        message = f"周报价更新完成，更新 {summary.get('updated_count', 0)} 条记录"
        if alias_hit_count:
            message = f"{message}，其中别名命中 {alias_hit_count} 条"
        if not_matched_count:
            message = (
                f"{message}，未匹配 {not_matched_count} 条，"
                f"去重后 {unique_not_matched_count} 个菜名"
            )

        warning_messages = list(summary.get("warnings", []))
        if summary.get("warning"):
            warning_messages.append(summary["warning"])
        if warning_messages:
            message = f"{message}。{warning_messages[0]}"

        return {
            "success": True,
            "message": message,
            "matched_count": summary.get("matched_count", 0),
            "updated_count": summary.get("updated_count", 0),
            "matched_items": summary.get("matched_items", []),
            "not_matched": summary.get("not_matched", []),
            "not_matched_count": not_matched_count,
            "not_matched_unique_count": unique_not_matched_count,
            "alias_hit_count": alias_hit_count,
            "warnings": warning_messages,
            "output_path": summary.get("output_path") or target_path,
            "backup_path": summary.get("backup_path"),
        }

    def list_aliases(self) -> dict:
        aliases = self._sorted_alias_items(get_weekly_price_aliases())
        return {
            "aliases": aliases,
            "total": len(aliases),
        }

    def upsert_aliases(self, mappings: dict[str, str]) -> dict:
        cleaned_mappings: dict[str, str] = {}
        for source_name, target_name in mappings.items():
            source = str(source_name or "").strip()
            target = str(target_name or "").strip()
            if not source or not target:
                raise ValueError("别名映射的源名称和目标名称都不能为空")
            cleaned_mappings[source] = target

        aliases = upsert_weekly_price_aliases(cleaned_mappings)
        alias_items = self._sorted_alias_items(aliases)
        return {
            "aliases": alias_items,
            "total": len(alias_items),
        }

    def delete_alias(self, source_name: str) -> dict:
        source = str(source_name or "").strip()
        if not source:
            raise ValueError("待删除的源名称不能为空")

        aliases = delete_weekly_price_alias(source)
        alias_items = self._sorted_alias_items(aliases)
        return {
            "aliases": alias_items,
            "total": len(alias_items),
        }

    def _sorted_alias_items(self, alias_map: dict[str, str]) -> list[dict[str, str]]:
        return [
            {
                "source_name": source_name,
                "target_name": target_name,
            }
            for source_name, target_name in sorted(
                alias_map.items(),
                key=lambda item: item[0].lower(),
            )
        ]

    def _validate_paths(self, update_path: str, reference_path: str) -> None:
        if not update_path or not os.path.exists(update_path):
                raise FileNotFoundError(f"待更新报价表不存在：{update_path}")
        if not reference_path or not os.path.exists(reference_path):
                raise FileNotFoundError(f"参考报价表不存在：{reference_path}")
