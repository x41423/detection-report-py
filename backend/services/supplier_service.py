"""Supplier service — 真实供应商（上游供货商）业务逻辑."""

from __future__ import annotations

from app.db.supplier_repository import SupplierRepository
from backend.models.supplier_schemas import SupplierCreate, SupplierResponse


class SupplierService:
    def __init__(self):
        self.repo = SupplierRepository()

    def list(self, search: str = "", status: str = "", limit: int = 20, offset: int = 0) -> dict:
        result = self.repo.list(search=search, status=status, limit=limit, offset=offset)
        return {"success": True, "items": result["items"], "total": result["total"]}

    def get(self, sid: int) -> dict:
        row = self.repo.get_by_id(sid)
        if not row:
            return {"success": False, "message": "供应商不存在"}
        return {"success": True, "item": row}

    def create(self, data: SupplierCreate) -> dict:
        sid = self.repo.create(data.model_dump())
        return {"success": True, "message": "供应商已创建", "id": sid}

    def update(self, sid: int, data: dict) -> dict:
        ok = self.repo.update(sid, data)
        if not ok:
            return {"success": False, "message": "更新失败"}
        return {"success": True, "message": "供应商已更新"}

    def delete(self, sid: int) -> dict:
        self.repo.delete(sid)
        return {"success": True, "message": "供应商已停用"}
