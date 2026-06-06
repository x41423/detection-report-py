"""Business logic for Product management."""

from __future__ import annotations

from typing import Any

from app.db.product_repository import ProductRepository
from backend.api.response_utils import list_response, mutation_response
from backend.models.product_schemas import (
    ProductCreate,
    ProductUpdate,
    ProductSkuCreate,
)


class ProductService:
    """Coordinate product CRUD with categories and SKUs."""

    def __init__(self) -> None:
        pass

    # ==================================================================
    # Product
    # ==================================================================

    def list_products(
        self,
        *,
        search: str = "",
        category_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
        include_inactive: bool = False,
    ) -> dict[str, Any]:
        result = ProductRepository.list_products(
            search=search, category_id=category_id, limit=limit, offset=offset,
            include_inactive=include_inactive,
        )
        items = result["items"]
        total = result["total"]
        return list_response(items, total, f"已加载 {len(items)} 条商品")

    def get_product(self, product_id: int) -> dict[str, Any]:
        product = ProductRepository.get_product(product_id)
        if product is None:
            raise LookupError(f"商品 {product_id} 不存在")
        return {"success": True, "message": "", "item": product}

    def create_product(self, data: ProductCreate) -> dict[str, Any]:
        pid = ProductRepository.create_product(data.model_dump())
        return mutation_response("商品已创建", id=pid)

    def update_product(self, product_id: int, data: ProductUpdate) -> dict[str, Any]:
        product = ProductRepository.get_product(product_id)
        if product is None:
            raise LookupError(f"商品 {product_id} 不存在")
        payload = data.model_dump(exclude_none=True)
        ProductRepository.update_product(product_id, payload)
        return mutation_response("商品已更新")

    def delete_product(self, product_id: int) -> dict[str, Any]:
        product = ProductRepository.get_product(product_id)
        if product is None:
            raise LookupError(f"商品 {product_id} 不存在")
        ProductRepository.delete_product(product_id)
        return mutation_response("商品已下架")

    def activate_product(self, product_id: int) -> dict[str, Any]:
        product = ProductRepository.get_product(product_id)
        if product is None:
            raise LookupError(f"商品 {product_id} 不存在")
        ProductRepository.activate_product(product_id)
        return mutation_response("商品已上架")

    # ==================================================================
    # Category
    # ==================================================================

    def list_categories(self) -> dict[str, Any]:
        items = ProductRepository.list_categories()
        return {"success": True, "items": items}

    def create_category(self, data: dict[str, Any]) -> dict[str, Any]:
        cat_id = ProductRepository.create_category(data)
        return {"success": True, "message": "分类已创建", "id": cat_id}

    def update_category(self, cat_id: int, data: dict[str, Any]) -> dict[str, Any]:
        ok = ProductRepository.update_category(cat_id, data)
        if not ok:
            return {"success": False, "message": "分类不存在"}
        return {"success": True, "message": "分类已更新"}

    def delete_category(self, cat_id: int) -> dict[str, Any]:
        ok = ProductRepository.delete_category(cat_id)
        if not ok:
            return {"success": False, "message": "分类不存在"}
        return {"success": True, "message": "分类已删除"}

    # ==================================================================
    # SKU
    # ==================================================================

    def list_skus(self, product_id: int) -> dict[str, Any]:
        product = ProductRepository.get_product(product_id)
        if product is None:
            raise LookupError(f"商品 {product_id} 不存在")
        items = ProductRepository.list_skus(product_id)
        return {"success": True, "items": items}

    def create_sku(self, product_id: int, data: ProductSkuCreate) -> dict[str, Any]:
        product = ProductRepository.get_product(product_id)
        if product is None:
            raise LookupError(f"商品 {product_id} 不存在")
        sku_id = ProductRepository.create_sku(product_id, data.model_dump())
        return mutation_response("规格已创建", id=sku_id)

    def update_sku(self, sku_id: int, data: ProductSkuCreate) -> dict[str, Any]:
        skus = ProductRepository.list_skus(0)  # check if SKU exists
        # Simple approach: try update, check rowcount
        payload = data.model_dump(exclude_none=True)
        updated = ProductRepository.update_sku(sku_id, payload)
        if not updated:
            raise LookupError(f"规格 {sku_id} 不存在")
        return mutation_response("规格已更新")
