"""Business logic for Purchase In / Return with inventory linkage."""
from __future__ import annotations

from datetime import date
from typing import Any

from app.db.purchase_repository import PurchaseRepository
from app.db.inventory_repository import InventoryRepository
from app.db.merchant_repository import MerchantRepository
from backend.api.response_utils import list_response, mutation_response
from backend.models.purchase_schemas import (
    PurchaseInCreate,
    PurchaseInUpdate,
    PurchaseReturnCreate,
    PurchaseReturnUpdate,
)


class PurchaseService:
    """Coordinate purchase CRUD, status transitions, and inventory sync."""

    def __init__(self) -> None:
        pass

    # ==================================================================
    # Purchase In
    # ==================================================================

    def create_in(self, data: PurchaseInCreate) -> dict[str, Any]:
        if MerchantRepository.get_by_id(data.supplier_id) is None:
            raise LookupError(f"供应商 {data.supplier_id} 不存在")

        payload = data.model_dump()
        rid = PurchaseRepository.create_in(payload)
        record = PurchaseRepository.get_in_by_id(rid)
        items = PurchaseRepository.get_in_items(rid)
        return mutation_response(
            "采购入库单已创建",
            record=self._serialize_in(record, items),
        )

    def list_in(
        self, *, search="", supplier_id=None, status=None, limit=20, offset=0
    ) -> dict[str, Any]:
        rows = PurchaseRepository.list_in(
            search=search, supplier_id=supplier_id, status=status,
            limit=limit, offset=offset,
        )
        total = PurchaseRepository.count_in(
            search=search, supplier_id=supplier_id, status=status,
        )
        items = [self._serialize_in_summary(r) for r in rows]
        return list_response(items, total, f"已加载 {len(items)} 条入库记录")

    def get_in(self, record_id: int) -> dict[str, Any]:
        record = PurchaseRepository.get_in_by_id(record_id)
        if record is None:
            raise LookupError(f"入库单 {record_id} 不存在")
        items = PurchaseRepository.get_in_items(record_id)
        return self._serialize_in(record, items)

    def update_in(self, record_id: int, data: PurchaseInUpdate) -> dict[str, Any]:
        record = PurchaseRepository.get_in_by_id(record_id)
        if record is None:
            raise LookupError(f"入库单 {record_id} 不存在")
        if record["status"] == "confirmed":
            raise ValueError("已确认的入库单不可修改")

        payload = data.model_dump(exclude_none=True)
        if not payload:
            raise ValueError("没有提供需要更新的字段")

        # only update header fields for now
        conn_kwargs = {"inbound_date": payload.get("inbound_date"), "remark": payload.get("remark")}
        # ... simple update via raw SQL approach
        from app.db.store import get_connection
        c = get_connection().cursor()
        try:
            sets = []
            vals = []
            if payload.get("inbound_date"):
                sets.append("inbound_date = ?")
                vals.append(payload["inbound_date"])
            if "remark" in payload:
                sets.append("remark = ?")
                vals.append(payload["remark"])
            if sets:
                vals.append(record_id)
                c.execute(
                    f"UPDATE PurchaseInRecord SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    vals,
                )
                get_connection().commit()
        finally:
            c.close()

        return self.get_in(record_id)

    def _write_inventory_txn(
        self,
        *,
        item: dict,
        business_date: str,
        direction: str,
        source_type: str,
        note: str,
    ) -> None:
        """Insert a single InventoryTransaction with correct source_ref_id."""
        from app.db.store import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            unit_id = InventoryRepository._get_or_create_unit_id(
                cursor, item.get("unit", "斤")
            )
            cursor.execute(
                """INSERT INTO InventoryTransaction
                   (veg_id, display_name, normalized_name, unit_id, direction,
                    quantity_delta, business_date, source_type, source_ref_id, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    None,
                    item["veg_name"],
                    item["veg_name"],
                    unit_id,
                    direction,
                    float(item["quantity"]),
                    business_date,
                    source_type,
                    item["id"],
                    note,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def confirm_in(self, record_id: int) -> dict[str, Any]:
        """Confirm an inbound record and sync inventory."""
        record = PurchaseRepository.get_in_by_id(record_id)
        if record is None:
            raise LookupError(f"入库单 {record_id} 不存在")
        if record["status"] == "confirmed":
            raise ValueError("入库单已确认，无需重复操作")

        items = PurchaseRepository.get_in_items(record_id)
        today = date.today().isoformat()

        for item in items:
            self._write_inventory_txn(
                item=item,
                business_date=record["inbound_date"] or today,
                direction="IN",
                source_type="purchase_in",
                note=f"采购入库 {record['order_no']}",
            )

        PurchaseRepository.update_in_status(record_id, "confirmed")
        return mutation_response("入库单已确认，库存已同步")

    # ==================================================================
    # Purchase Return
    # ==================================================================

    def create_return(self, data: PurchaseReturnCreate) -> dict[str, Any]:
        if MerchantRepository.get_by_id(data.supplier_id) is None:
            raise LookupError(f"供应商 {data.supplier_id} 不存在")

        rid = PurchaseRepository.create_return(data.model_dump())
        record = PurchaseRepository.get_return_by_id(rid)
        items = PurchaseRepository.get_return_items(rid)
        return mutation_response(
            "采购退货单已创建",
            record=self._serialize_return(record, items),
        )

    def list_return(
        self, *, search="", supplier_id=None, status=None, limit=20, offset=0
    ) -> dict[str, Any]:
        rows = PurchaseRepository.list_return(
            search=search, supplier_id=supplier_id, status=status,
            limit=limit, offset=offset,
        )
        total = PurchaseRepository.count_return(
            search=search, supplier_id=supplier_id, status=status,
        )
        items = [self._serialize_return_summary(r) for r in rows]
        return list_response(items, total, f"已加载 {len(items)} 条退货记录")

    def get_return(self, record_id: int) -> dict[str, Any]:
        record = PurchaseRepository.get_return_by_id(record_id)
        if record is None:
            raise LookupError(f"退货单 {record_id} 不存在")
        items = PurchaseRepository.get_return_items(record_id)
        return self._serialize_return(record, items)

    def confirm_return(self, record_id: int) -> dict[str, Any]:
        record = PurchaseRepository.get_return_by_id(record_id)
        if record is None:
            raise LookupError(f"退货单 {record_id} 不存在")
        if record["status"] == "confirmed":
            raise ValueError("退货单已确认，无需重复操作")

        items = PurchaseRepository.get_return_items(record_id)
        today = date.today().isoformat()

        for item in items:
            self._write_inventory_txn(
                item=item,
                business_date=record["return_date"] or today,
                direction="OUT",
                source_type="purchase_return",
                note=f"采购退货 {record['order_no']}",
            )

        PurchaseRepository.update_return_status(record_id, "confirmed")
        return mutation_response("退货单已确认，库存已同步")

    # ==================================================================
    # Serialization
    # ==================================================================

    @staticmethod
    def _serialize_in(record: dict, items: list[dict]) -> dict:
        return {
            "id": record["id"],
            "order_no": record["order_no"],
            "supplier_id": record["supplier_id"],
            "inbound_date": record["inbound_date"],
            "total_amount": record.get("total_amount", 0),
            "status": record["status"],
            "remark": record.get("remark"),
            "operator": record.get("operator"),
            "items": [
                {
                    "id": it["id"],
                    "veg_name": it["veg_name"],
                    "category": it.get("category"),
                    "unit": it.get("unit"),
                    "quantity": it["quantity"],
                    "unit_price": it["unit_price"],
                    "amount": it["amount"],
                    "tax_rate": it.get("tax_rate", 0),
                }
                for it in items
            ],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }

    @staticmethod
    def _serialize_in_summary(record: dict) -> dict:
        return {
            "id": record["id"],
            "order_no": record["order_no"],
            "supplier_id": record["supplier_id"],
            "supplier_name": record.get("supplier_name", ""),
            "inbound_date": record["inbound_date"],
            "total_amount": record.get("total_amount", 0),
            "status": record["status"],
            "remark": record.get("remark"),
            "operator": record.get("operator"),
            "created_at": record["created_at"],
        }

    @staticmethod
    def _serialize_return(record: dict, items: list[dict]) -> dict:
        return {
            "id": record["id"],
            "order_no": record["order_no"],
            "supplier_id": record["supplier_id"],
            "return_date": record["return_date"],
            "total_amount": record.get("total_amount", 0),
            "status": record["status"],
            "remark": record.get("remark"),
            "operator": record.get("operator"),
            "items": [
                {
                    "id": it["id"],
                    "veg_name": it["veg_name"],
                    "category": it.get("category"),
                    "unit": it.get("unit"),
                    "quantity": it["quantity"],
                    "unit_price": it["unit_price"],
                    "amount": it["amount"],
                }
                for it in items
            ],
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }

    @staticmethod
    def _serialize_return_summary(record: dict) -> dict:
        return {
            "id": record["id"],
            "order_no": record["order_no"],
            "supplier_id": record["supplier_id"],
            "supplier_name": record.get("supplier_name", ""),
            "return_date": record["return_date"],
            "total_amount": record.get("total_amount", 0),
            "status": record["status"],
            "remark": record.get("remark"),
            "operator": record.get("operator"),
            "created_at": record["created_at"],
        }
