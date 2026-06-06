"""MinIO 对象存储服务"""
from __future__ import annotations
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

def _load_env_file(filepath):
    result = {}
    p = Path(filepath)
    if not p.exists():
        return result
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result

_root = Path(__file__).resolve().parents[2]
_env = {**_load_env_file(str(_root / "config" / "minio.env"))}
_cr = _load_env_file(str(_root / "deploy" / "minio" / "credentials.env"))
if "MINIO_ROOT_USER" in _cr:
    _cr["MINIO_ACCESS_KEY"] = _cr.pop("MINIO_ROOT_USER")
if "MINIO_ROOT_PASSWORD" in _cr:
    _cr["MINIO_SECRET_KEY"] = _cr.pop("MINIO_ROOT_PASSWORD")
_env.update(_cr)

def _cfg(key, default=""):
    return os.environ.get(key, _env.get(key, default)).strip()

MINIO_ENDPOINT = _cfg("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = _cfg("MINIO_ACCESS_KEY", "minioadmin")
MINIO_BUCKET = _cfg("MINIO_BUCKET", "binxian-files")
MINIO_SECURE = _cfg("MINIO_SECURE", "false").lower() == "true"
USE_MINIO = _cfg("USE_MINIO", "false").lower() == "true"

_sk = _cfg("MINIO_SECRET_KEY", "minioadmin")

def is_minio_enabled():
    return USE_MINIO

class StorageService:
    def __init__(self):
        self._client = None
        self._initialized = False

    def _get_client(self):
        if self._client is None:
            from minio import Minio
            self._client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=_sk,
                secure=MINIO_SECURE,
            )
            logger.info("MinIO client init: %s (user=%s)", MINIO_ENDPOINT, MINIO_ACCESS_KEY)
        return self._client

    @property
    def client(self):
        return self._get_client()

    def _ensure_bucket(self):
        if self._initialized:
            return
        client = self._get_client()
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            logger.info("Created bucket: %s", MINIO_BUCKET)
        self._initialized = True

    def upload_file(self, file_data, object_name, content_type="application/octet-stream", length=None):
        self._ensure_bucket()
        client = self._get_client()
        if isinstance(file_data, bytes):
            data = BytesIO(file_data)
            if length is None:
                length = len(file_data)
        else:
            data = file_data
            if length is None:
                data.seek(0, 2)
                length = data.tell()
                data.seek(0)
        client.put_object(MINIO_BUCKET, object_name, data, length, content_type=content_type)
        path = f"/api/storage/{MINIO_BUCKET}/{object_name}"
        logger.info("Uploaded to MinIO: %s", path)
        return path

    def get_file_bytes(self, object_name):
        self._ensure_bucket()
        client = self._get_client()
        resp = client.get_object(MINIO_BUCKET, object_name)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def get_file_stream(self, object_name):
        self._ensure_bucket()
        return self._get_client().get_object(MINIO_BUCKET, object_name)

    def delete_file(self, object_name):
        try:
            self._ensure_bucket()
            self._get_client().remove_object(MINIO_BUCKET, object_name)
            return True
        except Exception as e:
            logger.error("Delete failed: %s", e)
            return False

    def file_exists(self, object_name):
        try:
            self._ensure_bucket()
            self._get_client().stat_object(MINIO_BUCKET, object_name)
            return True
        except Exception:
            return False

    def list_files(self, prefix=""):
        self._ensure_bucket()
        return [o.object_name for o in self._get_client().list_objects(MINIO_BUCKET, prefix=prefix, recursive=True) if o.object_name]

storage_service = StorageService()
