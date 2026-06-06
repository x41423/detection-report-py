"""Business logic for Quotation management."""

from __future__ import annotations

from typing import Any

from app.db.quotation_repository import QuotationRepository
from backend.api.response_utils import list_response, mutation_response
from backend.models.quotation_schemas import (
    QuotationCreate,
    QuotationUpdate,
    QuotationProductCreate,
    QuotationProductUpdate,
)


class QuotationService:
    """Coordinate quotation CRUD and product associations."""

    def __init__(self) -> None:
        pass

    # ==================================================================
    # Quotation
    # ==================================================================

    def list_quotations(
        self,
        *,
        search: str = "",
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        result = QuotationRepository.list_quotations(
            search=search, status=status, limit=limit, offset=offset,
        )
        items = result["items"]
        total = result["total"]
        return list_response(items, total, f"已加载 {len(items)} 条报价单")

    def get_quotation(self, quotation_id: int) -> dict[str, Any]:
        q = QuotationRepository.get_quotation(quotation_id)
        if q is None:
            raise LookupError(f"报价单 {quotation_id} 不存在")
        return {"success": True, "message": "", "item": q}

    def create_quotation(self, data: QuotationCreate) -> dict[str, Any]:
        qid = QuotationRepository.create_quotation(data.model_dump())
        return mutation_response("报价单已创建", id=qid)

    def update_quotation(self, quotation_id: int, data: QuotationUpdate) -> dict[str, Any]:
        q = QuotationRepository.get_quotation(quotation_id)
        if q is None:
            raise LookupError(f"报价单 {quotation_id} 不存在")
        payload = data.model_dump(exclude_none=True)
        QuotationRepository.update_quotation(quotation_id, payload)
        return mutation_response("报价单已更新")

    def toggle_status(self, quotation_id: int, status: str) -> dict[str, Any]:
        q = QuotationRepository.get_quotation(quotation_id)
        if q is None:
            raise LookupError(f"报价单 {quotation_id} 不存在")
        QuotationRepository.toggle_status(quotation_id, status)
        action = "激活" if status == "active" else "停用"
        return mutation_response(f"报价单已{action}")

    # ==================================================================
    # Quotation ↔ Product
    # ==================================================================

    def add_product(self, quotation_id: int, data: QuotationProductCreate) -> dict[str, Any]:
        q = QuotationRepository.get_quotation(quotation_id)
        if q is None:
            raise LookupError(f"报价单 {quotation_id} 不存在")
        qp_id = QuotationRepository.add_product(quotation_id, data.model_dump())
        return mutation_response("商品已添加到报价单", id=qp_id)

    def update_product(self, qp_id: int, data: QuotationProductUpdate) -> dict[str, Any]:
        QuotationRepository.update_product(qp_id, data.model_dump(exclude_none=True))
        return mutation_response("报价商品已更新")

    def remove_product(self, qp_id: int) -> dict[str, Any]:
        QuotationRepository.remove_product(qp_id)
        return mutation_response("商品已从报价单移除")
