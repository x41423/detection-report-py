"""Business logic for inventory balances and transactions."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from app.db.inventory_repository import InventoryRepository
from backend.services.daily_intake_service import DailyIntakeService


class InventoryService:
    """Coordinate stock-in, stock-out, adjustments, and balance queries."""

    def __init__(self) -> None:
        self._daily_intake_service = DailyIntakeService()

    def list_balances(
        self,
        *,
        search: str = "",
        limit: int = 200,
        include_zero: bool = False,
    ) -> dict[str, Any]:
        self._ensure_backfill()
        items = [
            self._serialize_balance(item)
            for item in InventoryRepository.list_balances(
                search=search,
                limit=limit,
                include_zero=include_zero,
            )
        ]
        return {
            "success": True,
            "message": f"已加载 {len(items)} 个库存条目",
            "items": items,
            "total": len(items),
        }

    def list_transactions(
        self,
        *,
        search: str = "",
        limit: int = 100,
        source_type: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_backfill()
        normalized_source_type = self._normalize_source_type_filter(source_type)
        items = [
            self._serialize_transaction(item)
            for item in InventoryRepository.list_transactions(
                search=search,
                limit=limit,
                source_type=normalized_source_type,
            )
        ]
        return {
            "success": True,
            "message": f"已加载 {len(items)} 条库存流水",
            "items": items,
            "total": len(items),
        }

    def export_balances_csv(
        self,
        *,
        search: str = "",
        include_zero: bool = False,
    ) -> tuple[str, str]:
        self._ensure_backfill()
        items = [
            self._serialize_balance(item)
            for item in InventoryRepository.list_balances(
                search=search,
                limit=1000,
                include_zero=include_zero,
            )
        ]

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["商品", "标准名", "单位", "库存", "流水数", "最近业务日期", "更新时间"])
        for item in items:
            writer.writerow(
                [
                    item["display_name"],
                    item["normalized_name"],
                    item["unit_name"],
                    item["available_quantity"],
                    item["transaction_count"],
                    item["last_business_date"] or "",
                    item["updated_at"] or "",
                ]
            )

        return buffer.getvalue(), "inventory-balances.csv"

    def create_outbound(
        self,
        *,
        business_date: str,
        name: str,
        unit: str,
        quantity: float,
        note: str = "",
    ) -> dict[str, Any]:
        self._ensure_backfill()
        item = self._daily_intake_service.normalize_inventory_item(name, unit)
        normalized_date = self._normalize_business_date(business_date)
        numeric_quantity = self._parse_positive_quantity(quantity, "出库数量")
        available_quantity = InventoryRepository.get_current_balance(
            item["normalized_name"],
            item["unit_name"],
        )
        if available_quantity + 1e-9 < numeric_quantity:
            raise ValueError(
                f"库存不足：当前可用 {available_quantity:.3f} {item['unit_name']}，无法出库 {numeric_quantity:.3f} {item['unit_name']}"
            )

        transaction = InventoryRepository.create_manual_transaction(
            display_name=item["display_name"],
            normalized_name=item["normalized_name"],
            veg_id=item["veg_id"],
            unit_name=item["unit_name"],
            direction="OUT",
            quantity_delta=-numeric_quantity,
            business_date=normalized_date,
            source_type=InventoryRepository.OUTBOUND_SOURCE,
            note=str(note or "").strip(),
        )
        return {
            "success": True,
            "message": "出库已登记",
            "transaction": self._serialize_transaction(transaction),
        }

    def update_outbound(
        self,
        transaction_id: int,
        *,
        business_date: str,
        name: str,
        unit: str,
        quantity: float,
        note: str = "",
    ) -> dict[str, Any]:
        self._ensure_backfill()
        current = self._get_manual_transaction(transaction_id, InventoryRepository.OUTBOUND_SOURCE)
        item = self._daily_intake_service.normalize_inventory_item(name, unit)
        normalized_date = self._normalize_business_date(business_date)
        numeric_quantity = self._parse_positive_quantity(quantity, "出库数量")
        available_quantity = InventoryRepository.get_current_balance(
            item["normalized_name"],
            item["unit_name"],
            exclude_transaction_id=transaction_id,
        )
        if available_quantity + 1e-9 < numeric_quantity:
            raise ValueError(
                f"库存不足：排除当前记录后可用 {available_quantity:.3f} {item['unit_name']}，无法更新为 {numeric_quantity:.3f} {item['unit_name']}"
            )

        transaction = InventoryRepository.update_manual_transaction(
            current["id"],
            display_name=item["display_name"],
            normalized_name=item["normalized_name"],
            veg_id=item["veg_id"],
            unit_name=item["unit_name"],
            direction="OUT",
            quantity_delta=-numeric_quantity,
            business_date=normalized_date,
            note=str(note or "").strip(),
        )
        return {
            "success": True,
            "message": "出库记录已更新",
            "transaction": self._serialize_transaction(transaction),
        }

    def delete_outbound(self, transaction_id: int) -> dict[str, Any]:
        self._ensure_backfill()
        current = self._get_manual_transaction(transaction_id, InventoryRepository.OUTBOUND_SOURCE)
        InventoryRepository.delete_transaction(current["id"])
        return {
            "success": True,
            "message": "出库记录已删除",
        }

    def create_adjustment(
        self,
        *,
        business_date: str,
        name: str,
        unit: str,
        target_quantity: float,
        note: str = "",
    ) -> dict[str, Any]:
        self._ensure_backfill()
        item = self._daily_intake_service.normalize_inventory_item(name, unit)
        normalized_date = self._normalize_business_date(business_date)
        target = self._parse_non_negative_quantity(target_quantity, "目标库存")
        current_balance = InventoryRepository.get_current_balance(
            item["normalized_name"],
            item["unit_name"],
        )
        delta = round(target - current_balance, 3)
        if abs(delta) <= 1e-9:
            raise ValueError("目标库存与当前库存一致，无需盘点修正")

        transaction = InventoryRepository.create_manual_transaction(
            display_name=item["display_name"],
            normalized_name=item["normalized_name"],
            veg_id=item["veg_id"],
            unit_name=item["unit_name"],
            direction="ADJUST",
            quantity_delta=delta,
            business_date=normalized_date,
            source_type=InventoryRepository.ADJUST_SOURCE,
            note=self._compose_adjustment_note(note, target),
        )
        return {
            "success": True,
            "message": "盘点修正已登记",
            "transaction": self._serialize_transaction(transaction),
        }

    def update_adjustment(
        self,
        transaction_id: int,
        *,
        business_date: str,
        name: str,
        unit: str,
        target_quantity: float,
        note: str = "",
    ) -> dict[str, Any]:
        self._ensure_backfill()
        current = self._get_manual_transaction(transaction_id, InventoryRepository.ADJUST_SOURCE)
        item = self._daily_intake_service.normalize_inventory_item(name, unit)
        normalized_date = self._normalize_business_date(business_date)
        target = self._parse_non_negative_quantity(target_quantity, "目标库存")
        current_balance = InventoryRepository.get_current_balance(
            item["normalized_name"],
            item["unit_name"],
            exclude_transaction_id=transaction_id,
        )
        delta = round(target - current_balance, 3)
        if abs(delta) <= 1e-9:
            raise ValueError("排除当前修正记录后，目标库存与当前库存一致")

        transaction = InventoryRepository.update_manual_transaction(
            current["id"],
            display_name=item["display_name"],
            normalized_name=item["normalized_name"],
            veg_id=item["veg_id"],
            unit_name=item["unit_name"],
            direction="ADJUST",
            quantity_delta=delta,
            business_date=normalized_date,
            note=self._compose_adjustment_note(note, target),
        )
        return {
            "success": True,
            "message": "盘点修正记录已更新",
            "transaction": self._serialize_transaction(transaction),
        }

    def delete_adjustment(self, transaction_id: int) -> dict[str, Any]:
        self._ensure_backfill()
        current = self._get_manual_transaction(transaction_id, InventoryRepository.ADJUST_SOURCE)
        InventoryRepository.delete_transaction(current["id"])
        return {
            "success": True,
            "message": "盘点修正记录已删除",
        }

    def _ensure_backfill(self) -> None:
        InventoryRepository.backfill_missing_daily_intake_transactions()

    def _get_manual_transaction(self, transaction_id: int, expected_source_type: str) -> dict[str, Any]:
        if transaction_id <= 0:
            raise ValueError("transaction_id 必须是正整数")

        transaction = InventoryRepository.get_transaction(transaction_id)
        if not transaction:
            raise KeyError("未找到库存流水记录")
        if transaction["source_type"] != expected_source_type:
            raise ValueError("该记录不属于当前操作类型")
        return transaction

    def _normalize_business_date(self, business_date: str) -> str:
        return self._daily_intake_service._normalize_intake_date(business_date)

    def _normalize_source_type_filter(self, source_type: str | None) -> str | None:
        normalized = str(source_type or "").strip()
        if not normalized:
            return None

        allowed = {
            InventoryRepository.DAILY_INTAKE_SOURCE,
            InventoryRepository.OUTBOUND_SOURCE,
            InventoryRepository.ADJUST_SOURCE,
        }
        if normalized not in allowed:
            raise ValueError(f"不支持的流水来源过滤值: {source_type}")
        return normalized

    def _parse_positive_quantity(self, value: float, field_label: str) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_label}必须是数字") from exc
        if numeric <= 0:
            raise ValueError(f"{field_label}必须大于 0")
        return round(numeric, 3)

    def _parse_non_negative_quantity(self, value: float, field_label: str) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_label}必须是数字") from exc
        if numeric < 0:
            raise ValueError(f"{field_label}不能小于 0")
        return round(numeric, 3)

    def _compose_adjustment_note(self, note: str, target_quantity: float) -> str:
        normalized_note = str(note or "").strip()
        target_note = f"target={target_quantity:.3f}"
        return f"{target_note}; {normalized_note}" if normalized_note else target_note

    def _split_adjustment_note(self, note: str) -> tuple[float | None, str]:
        normalized_note = str(note or "").strip()
        if not normalized_note.startswith("target="):
            return None, normalized_note

        first_part, separator, remainder = normalized_note.partition(";")
        raw_target = first_part.removeprefix("target=").strip()
        try:
            target_quantity = float(raw_target)
        except ValueError:
            return None, normalized_note
        return round(target_quantity, 3), remainder.strip() if separator else ""

    def _serialize_balance(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "display_name": item["display_name"] or item["normalized_name"],
            "normalized_name": item["normalized_name"],
            "veg_id": item["veg_id"],
            "unit_id": int(item["unit_id"]),
            "unit_name": item["unit_name"],
            "available_quantity": float(item["available_quantity"]),
            "transaction_count": int(item["transaction_count"]),
            "last_business_date": item["last_business_date"],
            "updated_at": item["updated_at"],
        }

    def _serialize_transaction(self, item: dict[str, Any]) -> dict[str, Any]:
        target_quantity, normalized_note = self._split_adjustment_note(item.get("note") or "")
        return {
            "id": int(item["id"]),
            "display_name": item["display_name"],
            "normalized_name": item["normalized_name"],
            "veg_id": item["veg_id"],
            "unit_id": int(item["unit_id"]),
            "unit_name": item["unit_name"],
            "direction": item["direction"],
            "quantity": float(item["quantity"]),
            "quantity_delta": float(item["quantity_delta"]),
            "business_date": item["business_date"],
            "source_type": item["source_type"],
            "source_ref_id": item["source_ref_id"],
            "target_quantity": target_quantity,
            "note": normalized_note,
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }
