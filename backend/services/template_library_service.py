from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from pathlib import Path

from backend.services.config_service import get_config, update_config
from shared.project_paths import get_project_paths


SMALL_TYPES = ["滨鲜", "1号", "5号", "6号", "7号", "8号", "顾家"]


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _template_root() -> Path:
    root = get_project_paths().data_dir / "templates"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_suffix(filename: str | None) -> str:
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in {".doc", ".docx"} else ".docx"


def _file_info(record: dict | str | None) -> dict:
    if isinstance(record, str):
        path = record
        filename = Path(record).name if record else ""
        updated_at = ""
    elif isinstance(record, dict):
        path = str(record.get("path") or "")
        filename = str(record.get("filename") or (Path(path).name if path else ""))
        updated_at = str(record.get("updated_at") or "")
    else:
        path = ""
        filename = ""
        updated_at = ""

    path_obj = Path(path) if path else None
    exists = bool(path_obj and path_obj.exists())
    return {
        "configured": exists,
        "path": str(path_obj) if exists else "",
        "filename": filename if exists else "",
        "updated_at": updated_at if exists else "",
    }


def _archive_previous_version(target_path: Path, target_dir: Path, kind: str) -> None:
    if not target_path.exists():
        return

    version_suffix = date.today().strftime("%Y-%m-%d")
    stem = target_path.stem
    suffix = target_path.suffix
    archived = target_dir / f"{stem}.{version_suffix}{suffix}"
    shutil.copy2(target_path, archived)

    versions_path = target_dir / "versions.json"
    versions = {}
    if versions_path.exists():
        try:
            with versions_path.open("r", encoding="utf-8") as f:
                versions = json.load(f)
        except Exception:
            pass

    key = f"pesticide_{kind}"
    if key not in versions:
        versions[key] = []

    versions[key].append({
        "version": len(versions[key]) + 1,
        "date": version_suffix,
        "file": archived.name,
    })

    with versions_path.open("w", encoding="utf-8") as f:
        json.dump(versions, f, ensure_ascii=False, indent=2)


def get_pesticide_templates() -> dict:
    templates = get_config().get("pesticide_templates") or {}
    return {
        "big_template": _file_info(templates.get("big")),
        "small_template": _file_info(templates.get("small")),
    }


def save_pesticide_template(kind: str, source_path: Path, original_name: str | None = None) -> dict:
    if kind not in {"big", "small"}:
        raise ValueError("模板类型只能是 big 或 small")

    target_dir = _template_root() / "pesticide"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{kind}-template{_safe_suffix(original_name)}"
    target_path = target_dir / target_name
    _archive_previous_version(target_path, target_dir, kind)
    shutil.copy2(source_path, target_path)

    cfg = get_config()
    templates = dict(cfg.get("pesticide_templates") or {})
    templates[kind] = {
        "path": str(target_path),
        "filename": original_name or target_name,
        "updated_at": _now_text(),
    }
    update_config({"pesticide_templates": templates})
    return get_pesticide_templates()


def get_transfer_templates() -> dict:
    configured = get_config().get("transfer_templates") or {}
    templates = {
        small_type: _file_info(configured.get(small_type))
        for small_type in SMALL_TYPES
    }

    # Backward compatibility: existing desktop config stored template paths under
    # "small_templates". Treat those as available templates until replaced.
    legacy_templates = get_config().get("small_templates") or {}
    for small_type, path in legacy_templates.items():
        if small_type in templates and not templates[small_type]["configured"]:
            templates[small_type] = _file_info(path)

    return {"templates": templates}


def save_transfer_template(small_type: str, source_path: Path, original_name: str | None = None) -> dict:
    small_type = (small_type or "").strip()
    if small_type not in SMALL_TYPES:
        raise ValueError("不支持的小表类型")

    target_dir = _template_root() / "transfer"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_name = f"{small_type}-template{_safe_suffix(original_name)}"
    target_path = target_dir / target_name
    shutil.copy2(source_path, target_path)

    cfg = get_config()
    templates = dict(cfg.get("transfer_templates") or {})
    templates[small_type] = {
        "path": str(target_path),
        "filename": original_name or target_name,
        "updated_at": _now_text(),
    }
    small_templates = dict(cfg.get("small_templates") or {})
    small_templates[small_type] = str(target_path)
    update_config({"transfer_templates": templates, "small_templates": small_templates})
    return get_transfer_templates()


def get_pesticide_template_path(kind: str) -> Path:
    templates = get_config().get("pesticide_templates") or {}
    info = _file_info(templates.get(kind))
    if not info["configured"]:
        label = "大表" if kind == "big" else "小表"
        raise FileNotFoundError(f"尚未保存农残检测{label}模板")
    return Path(info["path"])


def get_transfer_template_path(small_type: str) -> Path:
    info = get_transfer_templates()["templates"].get((small_type or "").strip())
    if not info or not info["configured"]:
        raise FileNotFoundError(f"尚未保存“{small_type}”小表模板")
    return Path(info["path"])


def get_pesticide_template_versions(kind: str) -> list[dict]:
    versions_path = _template_root() / "pesticide" / "versions.json"
    if not versions_path.exists():
        return []
    try:
        with versions_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(f"pesticide_{kind}", [])
    except Exception:
        return []


def rollback_pesticide_template(kind: str, version_date: str) -> dict:
    target_dir = _template_root() / "pesticide"
    target_name = f"{kind}-template.docx"
    target_path = target_dir / target_name

    archived_name = f"{kind}-template.{version_date}.docx"
    archived_path = target_dir / archived_name

    if not archived_path.exists():
        raise FileNotFoundError(f"版本不存在: {version_date}")

    _archive_previous_version(target_path, target_dir, kind)
    shutil.copy2(archived_path, target_path)

    cfg = get_config()
    templates = dict(cfg.get("pesticide_templates") or {})
    templates[kind] = {
        "path": str(target_path),
        "filename": target_name,
        "updated_at": _now_text(),
    }
    update_config({"pesticide_templates": templates})
    return get_pesticide_templates()


def delete_pesticide_template_version(kind: str, version_date: str) -> bool:
    target_dir = _template_root() / "pesticide"
    archived_name = f"{kind}-template.{version_date}.docx"
    archived_path = target_dir / archived_name

    if not archived_path.exists():
        return False
    archived_path.unlink()

    versions_path = target_dir / "versions.json"
    if versions_path.exists():
        try:
            with versions_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            key = f"pesticide_{kind}"
            if key in data:
                data[key] = [v for v in data[key] if v.get("date") != version_date]
            with versions_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return True
