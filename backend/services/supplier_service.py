"""Business logic for supplier management."""
from __future__ import annotations

from typing import Any

from app.db.supplier_repository import SupplierRepository
from backend.api.response_utils import list_response, mutation_response
from backend.models.supplier_schemas import SupplierCreate, SupplierUpdate


class SupplierService:
    """Coordinate supplier CRUD with validation and audit readiness."""

    def __init__(self) -> None:
        pass  # Aligns with InventoryService convention — no constructor deps.

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_supplier(self, data: SupplierCreate) -> dict[str, Any]:
        sid = SupplierRepository.create(data.model_dump())
        record = SupplierRepository.get_by_id(sid)
        return mutation_response("供应商创建成功", supplier=self._serialize(record))

    def list_suppliers(
        self,
        *,
        search: str = "",
        status: str | None = None,
        supplier_type: str | None = None,
        level: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        items = [
            self._serialize(item)
            for item in SupplierRepository.list(
                search=search, status=status, supplier_type=supplier_type,
                level=level, limit=limit, offset=offset
            )
        ]
        total = SupplierRepository.count(search=search, status=status, supplier_type=supplier_type, level=level)
        return list_response(items, total, f"已加载 {len(items)} 个供应商")

    def get_supplier(self, supplier_id: int) -> dict[str, Any]:
        record = SupplierRepository.get_by_id(supplier_id)
        if record is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")
        return self._serialize(record)

    def update_supplier(self, supplier_id: int, data: SupplierUpdate) -> dict[str, Any]:
        if SupplierRepository.get_by_id(supplier_id) is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")

        payload = data.model_dump(exclude_none=True)
        if not payload:
            raise ValueError("没有提供需要更新的字段")

        SupplierRepository.update(supplier_id, payload)
        record = SupplierRepository.get_by_id(supplier_id)
        return mutation_response("供应商信息已更新", supplier=self._serialize(record))

    def deactivate_supplier(self, supplier_id: int) -> dict[str, Any]:
        if SupplierRepository.get_by_id(supplier_id) is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")

        if SupplierRepository.has_purchase_records(supplier_id):
            raise ValueError("该供应商存在关联的采购入库记录，无法停用。请先处理关联单据。")

        SupplierRepository.deactivate(supplier_id)
        return mutation_response("供应商已停用")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "code": record["code"],
            "name": record["name"],
            "contact_person": record.get("contact_person"),
            "contact_phone": record.get("contact_phone"),
            "contact_address": record.get("contact_address"),
            "supplier_type": record.get("supplier_type", "enterprise"),
            "business_license": record.get("business_license"),
            "tax_number": record.get("tax_number"),
            "bank_name": record.get("bank_name"),
            "bank_account": record.get("bank_account"),
            "settlement_method": record.get("settlement_method", "monthly"),
            "payment_terms": record.get("payment_terms"),
            "credit_limit": record.get("credit_limit", 0),
            "level": record.get("level", "normal"),
            "status": record.get("status", "active"),
            "remark": record.get("remark"),
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
