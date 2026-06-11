"""日志查看 API。

提供日志文件的搜索、过滤、尾行功能，供中控台调用。
权限：system:view
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from backend.auth.dependencies import require_permission, get_current_auth_context

router = APIRouter()

# logs/ 目录相对于项目根目录
_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # backend/
_PROJECT_ROOT = _BACKEND_ROOT.parent
_LOG_DIR = _PROJECT_ROOT / "logs"

_VALID_FILES = frozenset({"app", "error", "access"})
MAX_LINES = 200
_LEVEL_ORDER = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}


def _resolve_log_path(file: str) -> Path:
    """将简名映射到实际文件路径。"""
    if file not in _VALID_FILES:
        file = "app"
    return _LOG_DIR / f"{file}.log"


def _parse_json_line(line: str) -> dict | None:
    """将 JSON 行解析为 dict。解析失败返回 None。"""
    try:
        return json.loads(line.strip())
    except (json.JSONDecodeError, ValueError):
        return None


def _filter_entries(
    lines: list[str],
    level: str = "",
    search: str = "",
    request_id: str = "",
) -> list[str]:
    """过滤日志行。"""
    result: list[str] = []
    level_upper = level.upper()
    search_lower = search.lower() if search else ""

    for line in lines:
        if not line.strip():
            continue

        # 级别过滤：解析 JSON 检查 level 字段
        if level_upper:
            entry = _parse_json_line(line)
            if entry and entry.get("level", "").upper() != level_upper:
                continue

        # 关键词搜索（大小写不敏感）
        if search_lower and search_lower not in line.lower():
            continue

        # 请求 ID 过滤
        if request_id:
            entry = _parse_json_line(line)
            if entry and entry.get("request_id") != request_id:
                continue

        result.append(line.rstrip("\n"))

    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/logs")
def list_logs(
    level: str = Query("", description="过滤级别: DEBUG/INFO/WARNING/ERROR/CRITICAL"),
    search: str = Query("", description="关键词搜索"),
    request_id: str = Query("", description="按 request_id 过滤"),
    limit: int = Query(50, ge=1, le=MAX_LINES, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    file: str = Query("app", description="日志文件: app/error/access"),
    _auth=Depends(require_permission("system:view")),
):
    """搜索 / 过滤日志。"""
    log_path = _resolve_log_path(file)
    if not log_path.exists():
        return {"success": True, "lines": [], "total": 0}

    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    # 从尾部往前读（最新的在前）
    all_lines.reverse()

    filtered = _filter_entries(all_lines, level=level, search=search,
                                request_id=request_id)
    total = len(filtered)
    paged = filtered[offset : offset + limit]

    return {
        "success": True,
        "lines": paged,
        "total": total,
        "file": file,
        "offset": offset,
        "limit": limit,
    }


@router.get("/logs/tail")
def tail_logs(
    lines: int = Query(20, ge=1, le=MAX_LINES, description="返回行数"),
    file: str = Query("app", description="日志文件: app/error/access"),
    _auth=Depends(require_permission("system:view")),
):
    """返回日志文件最后 N 行（最新的在前）。"""
    log_path = _resolve_log_path(file)
    if not log_path.exists():
        return {"success": True, "lines": [], "file": file}

    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
    tail.reverse()

    return {
        "success": True,
        "lines": [line.rstrip("\n") for line in tail],
        "file": file,
        "total_lines_in_file": len(all_lines),
    }


@router.get("/logs/stats")
def log_stats(
    _auth=Depends(require_permission("system:view")),
):
    """返回日志文件大小和各级别计数（最近 1000 行）。"""
    result: dict[str, dict] = {}
    for name in _VALID_FILES:
        path = _resolve_log_path(name)
        if not path.exists():
            result[name] = {"exists": False, "size_bytes": 0, "levels": {}}
            continue

        size = path.stat().st_size
        levels: dict[str, int] = {}

        with path.open("r", encoding="utf-8", errors="replace") as f:
            # 读最近 1000 行做统计
            all_lines = f.readlines()
            sample = all_lines[-1000:]

        for line in sample:
            entry = _parse_json_line(line)
            if entry:
                lvl = entry.get("level", "UNKNOWN")
                levels[lvl] = levels.get(lvl, 0) + 1

        result[name] = {
            "exists": True,
            "size_bytes": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "total_lines": len(all_lines),
            "levels": levels,
        }

    return {"success": True, "files": result}
