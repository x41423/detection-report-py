"""Business logic for supplier management."""
from __future__ import annotations

from typing import Any

from app.db.merchant_repository import MerchantRepository
from app.db.order_repository import OrderRepository
from app.db.store import query_one
from backend.api.response_utils import list_response, mutation_response
from backend.models.merchant_schemas import MerchantCreate, MerchantUpdate


class MerchantService:
    """Coordinate supplier CRUD with validation and audit readiness."""

    def __init__(self) -> None:
        pass  # Aligns with InventoryService convention — no constructor deps.

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_supplier(self, data: MerchantCreate) -> dict[str, Any]:
        # 同名检测
        existing = MerchantRepository.get_by_name(data.name)
        if existing:
            raise ValueError(f"同名商户「{data.name}」已存在，请勿重复创建")
        sid = MerchantRepository.create(data.model_dump())
        record = MerchantRepository.get_by_id(sid)
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
            for item in MerchantRepository.list(
                search=search, status=status, supplier_type=supplier_type,
                level=level, limit=limit, offset=offset
            )
        ]
        total = MerchantRepository.count(search=search, status=status, supplier_type=supplier_type, level=level)
        return list_response(items, total, f"已加载 {len(items)} 个供应商")

    def get_supplier(self, supplier_id: int) -> dict[str, Any]:
        record = MerchantRepository.get_by_id(supplier_id)
        if record is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")
        return self._serialize(record)

    def update_supplier(self, supplier_id: int, data: MerchantUpdate) -> dict[str, Any]:
        if MerchantRepository.get_by_id(supplier_id) is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")

        payload = data.model_dump(exclude_none=True)
        if not payload:
            raise ValueError("没有提供需要更新的字段")

        MerchantRepository.update(supplier_id, payload)
        record = MerchantRepository.get_by_id(supplier_id)
        return mutation_response("供应商信息已更新", supplier=self._serialize(record))

    def deactivate_supplier(self, supplier_id: int) -> dict[str, Any]:
        if MerchantRepository.get_by_id(supplier_id) is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")

        if MerchantRepository.has_purchase_records(supplier_id):
            raise ValueError("该供应商存在关联的采购入库记录，无法停用。请先处理关联单据。")

        MerchantRepository.deactivate(supplier_id)
        return mutation_response("供应商已停用")

    def activate_supplier(self, supplier_id: int) -> dict[str, Any]:
        """重新启用已停用的供应商"""
        record = MerchantRepository.get_by_id(supplier_id)
        if record is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")
        if record["status"] != "inactive":
            raise ValueError("仅已停用的供应商可启用")
        MerchantRepository.update(supplier_id, {"status": "active"})
        return mutation_response("供应商已启用")

    def hard_delete_supplier(self, supplier_id: int) -> dict[str, Any]:
        """硬删除供应商（无关联采购记录才能删）"""
        if MerchantRepository.get_by_id(supplier_id) is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")
        if MerchantRepository.has_purchase_records(supplier_id):
            raise ValueError("该供应商存在关联的采购入库记录，无法删除。请先处理关联单据。")
        MerchantRepository.hard_delete(supplier_id)
        return mutation_response("供应商已永久删除")

    def get_transaction_summary(
        self, supplier_id: int, *, date_from: str | None = None, date_to: str | None = None,
    ) -> dict[str, Any]:
        """Aggregate order statistics for a supplier (matching 观麦 交易情况 tab)."""
        supplier = MerchantRepository.get_by_id(supplier_id)
        if supplier is None:
            raise LookupError(f"供应商 {supplier_id} 不存在")

        name = supplier["name"]
        # 注意：当前通过 merchant_name 精确匹配关联订单与供应商
        # 若供应商名在 OrderRecord.merchant_name 中不存在，统计数据会为 0
        clause = "WHERE o.merchant_name = ?"
        params: list[Any] = [name]

        if date_from:
            clause += " AND o.order_date >= ?"
            params.append(date_from)
        if date_to:
            clause += " AND o.order_date <= ?"
            params.append(date_to)

        row = query_one(
            f"""SELECT
                  COALESCE(SUM(oi.amount), 0) AS total_sales,
                  COUNT(DISTINCT o.id) AS order_count,
                  COALESCE(SUM(o.discount_amount), 0) AS total_discount,
                  COALESCE(SUM(o.freight), 0) AS total_freight,
                  COALESCE(SUM(o.after_sale_amount), 0) AS after_sale_amount,
                  COALESCE(SUM(o.should_refund_amount), 0) AS should_refund
               FROM OrderItem oi
               JOIN OrderRecord o ON oi.order_id = o.id
               {clause}""",
            tuple(params),
        )
        if row:
            total_sales = float(row["total_sales"] or 0)
            total_freight = float(row["total_freight"] or 0)
            total_discount = float(row["total_discount"] or 0)
            sales_excl_freight = total_sales - total_freight

            # Cost estimation (~75% of sales for rough margin)
            estimated_cost = total_sales * 0.75
            gross_margin = total_sales - estimated_cost - total_discount

            return {
                "success": True,
                "total_sales_amount": round(total_sales, 2),
                "total_sales_amount_excl_freight": round(sales_excl_freight, 2),
                "total_gross_margin": round(gross_margin, 2),
                "gross_margin_rate": round(gross_margin / total_sales * 100, 2) if total_sales > 0 else 0,
                "total_discount": round(total_discount, 2),
                "order_count": int(row["order_count"] or 0),
                "after_sale_count": 0,
                "abnormal_amount": round(float(row["after_sale_amount"] or 0), 2),
                "should_refund": round(float(row["should_refund"] or 0), 2),
                "actual_refund": 0,
            }
        return {
            "success": True,
            "total_sales_amount": 0, "total_sales_amount_excl_freight": 0,
            "total_gross_margin": 0, "gross_margin_rate": 0,
            "total_discount": 0, "order_count": 0,
            "after_sale_count": 0, "abnormal_amount": 0,
            "should_refund": 0, "actual_refund": 0,
        }

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
            # 结算配置
            "settlement_person": record.get("settlement_person"),
            "settlement_phone": record.get("settlement_phone"),
            "date_dimension": record.get("date_dimension", "order_date"),
            "period_start_day": record.get("period_start_day", 1),
            "settlement_day": record.get("settlement_day", 1),
            "freeze_status": record.get("freeze_status", 0),
            "approval_status": record.get("approval_status", 1),
            "sorting_priority": record.get("sorting_priority", 0),
            "created_at": record["created_at"],
            "updated_at": record["updated_at"],
        }
