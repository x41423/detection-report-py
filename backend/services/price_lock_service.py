"""Price Lock service."""
from __future__ import annotations

from typing import Any

from app.db.price_lock_repository import PriceLockRepository
from backend.api.response_utils import list_response, mutation_response
from backend.models.price_lock_schemas import PriceLockCreate, PriceLockUpdate


class PriceLockService:
    def __init__(self) -> None:
        pass

    def create(self, data: PriceLockCreate) -> dict[str, Any]:
        rid = PriceLockRepository.create(data.model_dump())
        record = PriceLockRepository.get_by_id(rid)
        items = PriceLockRepository.get_items(rid)
        return mutation_response("锁价规则已创建", record=self._serialize(record, items))

    def list_rules(self, *, search="", status=None, limit=20, offset=0) -> dict[str, Any]:
        rows = PriceLockRepository.list_rules(search=search, status=status, limit=limit, offset=offset)
        total = PriceLockRepository.count_rules(search=search, status=status)
        items = [self._serialize(r, PriceLockRepository.get_items(r["id"])) for r in rows]
        return list_response(items, total, f"已加载 {len(items)} 条锁价规则")

    def get(self, rule_id: int) -> dict[str, Any]:
        record = PriceLockRepository.get_by_id(rule_id)
        if record is None:
            raise LookupError(f"锁价规则 {rule_id} 不存在")
        return self._serialize(record, PriceLockRepository.get_items(rule_id))

    def update(self, rule_id: int, data: PriceLockUpdate) -> dict[str, Any]:
        if PriceLockRepository.get_by_id(rule_id) is None:
            raise LookupError(f"锁价规则 {rule_id} 不存在")
        PriceLockRepository.update(rule_id, data.model_dump(exclude_none=True))
        return self.get(rule_id)

    def deactivate(self, rule_id: int) -> dict[str, Any]:
        if PriceLockRepository.get_by_id(rule_id) is None:
            raise LookupError(f"锁价规则 {rule_id} 不存在")
        PriceLockRepository.deactivate(rule_id)
        return mutation_response("锁价规则已停用")

    @staticmethod
    def _serialize(record: dict, items: list[dict]) -> dict:
        return {
            "id": record["id"],
            "rule_code": record["rule_code"],
            "rule_name": record["rule_name"],
            "salemenu_id": record.get("salemenu_id"),
            "salemenu_name": record.get("salemenu_name"),
            "target_count": record.get("target_count", 0),
            "category_count": record.get("category_count", 0),
            "start_time": record.get("start_time"),
            "end_time": record.get("end_time"),
            "status": record.get("status"),
            "operator": record.get("operator"),
            "items": [
                {"id": it["id"], "veg_name": it["veg_name"], "locked_price": it["locked_price"]}
                for it in items
            ],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
