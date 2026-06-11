"""Business logic for Supplier Settlement with auto-calculation."""
from __future__ import annotations

from typing import Any

from app.db.settlement_repository import SettlementRepository
from app.db.merchant_repository import MerchantRepository
from backend.api.response_utils import list_response, mutation_response
from backend.models.settlement_schemas import SettlementCreate, SettlementUpdate


class SettlementService:
    """Coordinate settlement CRUD and auto-calc from purchase records."""

    def __init__(self) -> None:
        pass

    def create(self, data: SettlementCreate) -> dict[str, Any]:
        if MerchantRepository.get_by_id(data.supplier_id) is None:
            raise LookupError(f"供应商 {data.supplier_id} 不存在")

        payload = data.model_dump()
        rid = SettlementRepository.create(payload)
        record = SettlementRepository.get_by_id(rid)
        return mutation_response(
            "结算单已创建",
            record=self._serialize(record),
        )

    def list_settlements(
        self, *, supplier_id=None, period=None, status=None, limit=20, offset=0,
    ) -> dict[str, Any]:
        rows = SettlementRepository.list_settlements(
            supplier_id=supplier_id, period=period, status=status,
            limit=limit, offset=offset,
        )
        total = SettlementRepository.count_settlements(
            supplier_id=supplier_id, period=period, status=status,
        )
        items = [self._serialize(r) for r in rows]
        return list_response(items, total, f"已加载 {len(items)} 条结算记录")

    def get(self, settlement_id: int) -> dict[str, Any]:
        record = SettlementRepository.get_by_id(settlement_id)
        if record is None:
            raise LookupError(f"结算单 {settlement_id} 不存在")
        return self._serialize(record)

    def update(self, settlement_id: int, data: SettlementUpdate) -> dict[str, Any]:
        record = SettlementRepository.get_by_id(settlement_id)
        if record is None:
            raise LookupError(f"结算单 {settlement_id} 不存在")
        if record["status"] == "settled":
            raise ValueError("已结算记录不可修改")

        payload = data.model_dump(exclude_none=True)
        SettlementRepository.update(settlement_id, payload)
        return self.get(settlement_id)

    def confirm(self, settlement_id: int) -> dict[str, Any]:
        record = SettlementRepository.get_by_id(settlement_id)
        if record is None:
            raise LookupError(f"结算单 {settlement_id} 不存在")
        if record["status"] == "settled":
            raise ValueError("结算单已确认，无需重复操作")
        SettlementRepository.update_status(settlement_id, "settled")
        return mutation_response("结算单已确认")

    def auto_create(self, supplier_id: int, period: str) -> dict[str, Any]:
        """Auto-create settlement from confirmed purchase-in records for a period."""
        if MerchantRepository.get_by_id(supplier_id) is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")

        payable = SettlementRepository.get_payable_for_period(supplier_id, period)
        if payable == 0:
            raise ValueError(f"供应商 {supplier_id} 在 {period} 期间无已确认入库记录")

        rid = SettlementRepository.create({
            "supplier_id": supplier_id,
            "settlement_period": period,
            "payable_amount": payable,
        })
        record = SettlementRepository.get_by_id(rid)
        return mutation_response(
            f"已为 {period} 期间自动生成结算单，应结金额 ¥{payable:,.2f}",
            record=self._serialize(record),
        )

    @staticmethod
    def _serialize(record: dict) -> dict:
        return {
            "id": record["id"],
            "supplier_id": record["supplier_id"],
            "supplier_name": record.get("supplier_name"),
            "settlement_period": record["settlement_period"],
            "payable_amount": record.get("payable_amount", 0),
            "paid_amount": record.get("paid_amount", 0),
            "fee_amount": record.get("fee_amount", 0),
            "discount_amount": record.get("discount_amount", 0),
            "balance_amount": record.get("balance_amount", 0),
            "reconciliation_status": record.get("reconciliation_status", "pending"),
            "status": record.get("status", "pending"),
            "remark": record.get("remark"),
            "operator": record.get("operator"),
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
