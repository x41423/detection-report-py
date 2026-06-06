"""
将本地 uploads/products/ 下的图片迁移到 MinIO
并更新数据库中的 image_url 字段

使用方法:
    1. 先启动 MinIO 服务: deploy\\minio\\start-minio.bat
    2. 运行脚本: python scripts/migrate_files_to_minio.py
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# 确保项目根目录在 sys.path 中
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

UPLOADS_DIR = ROOT_DIR / "data" / "uploads" / "products"


def load_minio_env():
    """从 config/minio.env 加载配置"""
    env_path = ROOT_DIR / "config" / "minio.env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def get_db_connection():
    """获取数据库连接"""
    from app.db.store import get_connection
    return get_connection()


def migrate_images():
    """迁移图片文件到MinIO"""
    from backend.services.storage_service import storage_service, MINIO_BUCKET

    if not UPLOADS_DIR.exists():
        print(f"[跳过] 本地图片目录不存在: {UPLOADS_DIR}")
        return

    # 获取所有图片文件
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp"]:
        image_files.extend(UPLOADS_DIR.glob(ext))

    if not image_files:
        print("[跳过] 没有找到本地图片文件")
        return

    print(f"[信息] 找到 {len(image_files)} 个图片文件待迁移")

    conn = get_db_connection()
    cursor = conn.cursor()

    migrated = 0
    skipped = 0
    errors = 0

    for img_path in image_files:
        filename = img_path.name
        old_url = f"/uploads/products/{filename}"

        try:
            # 查询是否有商品使用此图片
            cursor.execute(
                "SELECT id FROM Product WHERE image_url = ?", (old_url,)
            )
            rows = cursor.fetchall()

            if not rows:
                skipped += 1
                continue

            # 上传到MinIO
            content = img_path.read_bytes()
            suffix = img_path.suffix or ".jpg"
            object_name = f"products/{uuid.uuid4().hex}/{filename}"

            # 猜测MIME类型
            mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".png": "image/png", ".gif": "image/gif",
                        ".webp": "image/webp"}
            content_type = mime_map.get(suffix.lower(), "image/jpeg")

            new_url = storage_service.upload_file(
                file_data=content,
                object_name=object_name,
                content_type=content_type,
            )

            # 更新数据库
            for row in rows:
                product_id = row[0] if isinstance(row, tuple) else row["id"]
                cursor.execute(
                    "UPDATE Product SET image_url = ? WHERE id = ?",
                    (new_url, product_id),
                )
                print(f"  [更新] 商品ID={product_id}: {old_url} -> {new_url}")

            conn.commit()
            migrated += 1

        except Exception as e:
            print(f"  [错误] {filename}: {e}")
            errors += 1
            conn.rollback()

    cursor.close()
    conn.close()

    print(f"\n[完成] 迁移统计:")
    print(f"  - 已迁移: {migrated}")
    print(f"  - 已跳过: {skipped}")
    print(f"  - 错误:   {errors}")


if __name__ == "__main__":
    load_minio_env()
    os.environ.setdefault("USE_MINIO", "true")

    from backend.services.storage_service import MINIO_ENDPOINT, MINIO_BUCKET

    print("=" * 60)
    print("  本地图片迁移至 MinIO")
    print("=" * 60)
    print(f"  本地目录: {UPLOADS_DIR}")
    print(f"  MinIO端点: {MINIO_ENDPOINT}")
    print(f"  存储桶: {MINIO_BUCKET}")
    print()

    try:
        migrate_images()
    except Exception as e:
        print(f"\n[致命错误] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
