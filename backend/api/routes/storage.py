"""MinIO 文件访问路由"""

from __future__ import annotations

import logging
from mimetypes import guess_type

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend.auth.dependencies import require_permission
from backend.services.storage_service import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/{bucket}/{object_path:path}", dependencies=[Depends(require_permission("storage:view"))])
async def get_file(bucket: str, object_path: str):
    """
    从MinIO获取文件

    URL格式: /api/storage/{bucket}/{object_path}
    示例: /api/storage/binxian-files/products/abc123.jpg
    """
    # 验证bucket（只允许配置的桶名）
    from backend.services.storage_service import MINIO_BUCKET
    if bucket != MINIO_BUCKET:
        raise HTTPException(status_code=404, detail="存储桶不存在")

    try:
        # 获取文件内容
        file_bytes = storage_service.get_file_bytes(object_path)

        # 猜测MIME类型
        content_type, _ = guess_type(object_path)
        if not content_type:
            content_type = "application/octet-stream"

        return Response(
            content=file_bytes,
            media_type=content_type,
        )
    except Exception as e:
        logger.error("获取MinIO文件失败: %s/%s, 错误: %s", bucket, object_path, e)
        raise HTTPException(status_code=404, detail="文件不存在")
