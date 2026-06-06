"""Inspection report service — business logic layer."""

from __future__ import annotations

from app.db.inspection_report_repository import InspectionReportRepository as Repo
from backend.api.response_utils import list_response, mutation_response


class InspectionReportService:
    """No-arg constructor — follows project convention."""

    def create(self, data: dict, user_id: int) -> dict:
        data["uploaded_by"] = user_id
        report_id = Repo.create_report(data)
        record = Repo.get_report(report_id)
        return mutation_response("检测报告已创建", record=record)

    def update(self, report_id: int, data: dict) -> dict:
        ok = Repo.update_report(report_id, data)
        if not ok:
            return {"success": False, "message": "报告不存在"}
        record = Repo.get_report(report_id)
        return mutation_response("检测报告已更新", record=record)

    def list_reports(
        self,
        search: str = "",
        status: str = "",
        supplier_id: int = 0,
        test_date_from: str = "",
        test_date_to: str = "",
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        items = Repo.list_reports(
            search=search,
            status=status,
            supplier_id=supplier_id,
            test_date_from=test_date_from,
            test_date_to=test_date_to,
            limit=limit,
            offset=offset,
        )
        total = Repo.count_reports(
            search=search,
            status=status,
            supplier_id=supplier_id,
            test_date_from=test_date_from,
            test_date_to=test_date_to,
        )
        return list_response(items, total, f"已加载 {len(items)} 条记录")

    def get_report(self, report_id: int) -> dict:
        record = Repo.get_report(report_id)
        if record is None:
            return {"success": False, "message": "报告不存在"}
        return {"success": True, "item": record}

    def delete_report(self, report_id: int) -> dict:
        ok = Repo.delete_report(report_id)
        if not ok:
            return {"success": False, "message": "报告不存在"}
        return {"success": True, "message": "检测报告已删除"}
