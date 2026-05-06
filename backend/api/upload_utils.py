from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response

_FILENAME_SANITIZE_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def _encode_header_value(value: str) -> str:
    """Make an HTTP header value latin-1 safe by percent-encoding non-ASCII chars."""
    text = "" if value is None else str(value)
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return quote(text, safe=" ;=,.-_/()[]")


def sanitize_filename(raw_name: str | None, fallback_stem: str, default_suffix: str = "") -> str:
    candidate = Path(str(raw_name or "")).name.strip()
    if not candidate:
        candidate = fallback_stem
    stem = _FILENAME_SANITIZE_RE.sub("-", Path(candidate).stem).strip(".- ") or fallback_stem
    suffix = Path(candidate).suffix or default_suffix
    return f"{stem}{suffix}"


async def save_upload(upload: UploadFile, target_dir: Path, fallback_stem: str) -> Path:
    if upload is None:
        raise HTTPException(status_code=400, detail="缺少上传文件")

    filename = sanitize_filename(upload.filename, fallback_stem)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    content = await upload.read()
    target_path.write_bytes(content)
    await upload.close()
    return target_path


async def save_uploads(
    uploads: list[UploadFile] | None,
    target_dir: Path,
    fallback_prefix: str,
) -> list[Path]:
    if not uploads:
        raise HTTPException(status_code=400, detail="至少需要上传一个文件")

    saved_paths: list[Path] = []
    for index, upload in enumerate(uploads, start=1):
        saved_paths.append(await save_upload(upload, target_dir, f"{fallback_prefix}-{index}"))
    return saved_paths


def parse_json_form_value(raw_text: str, *, field_name: str, expected_type: type) -> Any:
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 不是合法 JSON") from exc

    if not isinstance(value, expected_type):
        raise HTTPException(status_code=400, detail=f"{field_name} 的 JSON 类型不正确")
    return value


def build_download_response(
    file_path: Path,
    *,
    media_type: str,
    download_name: str | None = None,
    extra_headers: dict[str, str] | None = None,
) -> Response:
    filename = download_name or file_path.name
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
    }
    if extra_headers:
        for key, value in extra_headers.items():
            headers[key] = _encode_header_value(value)
    return Response(
        content=file_path.read_bytes(),
        media_type=media_type,
        headers=headers,
    )


def create_zip_archive(zip_path: Path, files: list[Path], *, arc_root: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, arcname=str(file_path.relative_to(arc_root)))
    return zip_path
