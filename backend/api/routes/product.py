"""Product management API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pathlib import Path

from backend.auth.dependencies import require_permission
from backend.api.upload_utils import save_upload
from backend.models.product_schemas import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    ProductSkuCreate,
)
from backend.services.product_service import ProductService

router = APIRouter()
service = ProductService()


def _raise(exc: Exception) -> None:
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


# ==================================================================
# Product
# ==================================================================


@router.get(
    "/",
    dependencies=[Depends(require_permission("product:view"))],
)
def list_products(
    search: str = Query(default=""),
    category_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_inactive: bool = Query(default=False),
):
    try:
        return service.list_products(
            search=search, category_id=category_id, limit=limit, offset=offset,
            include_inactive=include_inactive,
        )
    except ValueError as exc:
        _raise(exc)


@router.get(
    "/categories",
    dependencies=[Depends(require_permission("category:view"))],
)
def list_categories():
    try:
        return service.list_categories()
    except Exception as exc:
        _raise(exc)


# ==================================================================
# Image Upload — MUST be before /{product_id} to avoid 405
# ==================================================================

import os
import uuid

UPLOADS_DIR = Path(__file__).resolve().parents[3] / "data" / "uploads" / "products"


@router.post(
    "/upload-image",
    dependencies=[Depends(require_permission("product:create"))],
)
async def upload_product_image(file: UploadFile = File(...)):
    """Upload a product image, returns the accessible URL."""
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只允许上传图片文件")

    from backend.services.storage_service import is_minio_enabled, storage_service

    if is_minio_enabled():
        # MinIO存储
        content = await file.read()
        filename = sanitize_filename(file.filename, "product")
        object_name = f"products/{uuid.uuid4().hex}/{filename}"
        url = storage_service.upload_file(
            file_data=content,
            object_name=object_name,
            content_type=file.content_type or "image/jpeg",
        )
        await file.close()
    else:
        # 本地存储（原有逻辑）
        saved_path = await save_upload(file, UPLOADS_DIR, fallback_stem="product")
        url = f"/uploads/products/{saved_path.name}"

    return {"success": True, "message": "图片上传成功", "url": url}


def sanitize_filename(raw_name: str | None, fallback: str) -> str:
    """提取安全的文件名"""
    import re
    from pathlib import Path as P
    candidate = P(str(raw_name or "")).name.strip()
    if not candidate:
        return fallback
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", P(candidate).stem).strip(".- ") or fallback
    suffix = P(candidate).suffix or ".jpg"
    return f"{stem}{suffix}"


@router.get(
    "/{product_id}",
    dependencies=[Depends(require_permission("product:view"))],
)
def get_product(product_id: int):
    try:
        return service.get_product(product_id)
    except LookupError as exc:
        _raise(exc)


@router.post(
    "/",
    dependencies=[Depends(require_permission("product:create"))],
)
def create_product(data: ProductCreate):
    try:
        return service.create_product(data)
    except Exception as exc:
        _raise(exc)


@router.put(
    "/{product_id}",
    dependencies=[Depends(require_permission("product:update"))],
)
def update_product(product_id: int, data: ProductUpdate):
    try:
        return service.update_product(product_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.delete(
    "/{product_id}",
    dependencies=[Depends(require_permission("product:delete"))],
)
def delete_product(product_id: int):
    try:
        return service.delete_product(product_id)
    except LookupError as exc:
        _raise(exc)


@router.put(
    "/{product_id}/activate",
    dependencies=[Depends(require_permission("product:update"))],
)
def activate_product(product_id: int):
    try:
        return service.activate_product(product_id)
    except LookupError as exc:
        _raise(exc)


# ==================================================================
# SKU
# ==================================================================


@router.get(
    "/{product_id}/skus",
    dependencies=[Depends(require_permission("product:view"))],
)
def list_skus(product_id: int):
    try:
        return service.list_skus(product_id)
    except LookupError as exc:
        _raise(exc)


@router.post(
    "/{product_id}/skus",
    dependencies=[Depends(require_permission("product:create"))],
)
def create_sku(product_id: int, data: ProductSkuCreate):
    try:
        return service.create_sku(product_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


@router.put(
    "/skus/{sku_id}",
    dependencies=[Depends(require_permission("product:update"))],
)
def update_sku(sku_id: int, data: ProductSkuCreate):
    try:
        return service.update_sku(sku_id, data)
    except (LookupError, ValueError) as exc:
        _raise(exc)


# ==================================================================
# Category management (P1.2)
# ==================================================================

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    parent_id: int = 0
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


@router.post(
    "/categories",
    dependencies=[Depends(require_permission("product:create"))],
)
def create_category(body: CategoryCreate):
    try:
        result = service.create_category(body.model_dump())
        return result
    except Exception as exc:
        _raise(exc)


@router.put(
    "/categories/{cat_id}",
    dependencies=[Depends(require_permission("product:update"))],
)
def update_category(cat_id: int, body: CategoryUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    try:
        return service.update_category(cat_id, data)
    except Exception as exc:
        _raise(exc)


@router.delete(
    "/categories/{cat_id}",
    dependencies=[Depends(require_permission("product:delete"))],
)
def delete_category(cat_id: int):
    try:
        return service.delete_category(cat_id)
    except Exception as exc:
        _raise(exc)
