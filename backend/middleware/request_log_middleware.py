"""全量 HTTP 请求日志中间件。

功能：
- 每个请求注入 request_id（X-Request-ID 头）
- 记录 access log（method / path / status / duration_ms）
- 慢请求检测（>1000ms → WARNING）
- 请求体 / 响应体捕获（自动脱敏、截断）
- 内存滚动性能统计（PerfStats）
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from threading import Lock
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.middleware._request_meta import client_ip, user_agent as _user_agent
from shared.request_context import get_request_id, set_request_context

# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------

SLOW_REQUEST_THRESHOLD_MS = 1000
BODY_MAX_LENGTH = 4096                # 请求/响应体截断阈值
PERF_WINDOW_SIZE = 1000               # 性能统计窗口大小
_SENSITIVE_FIELDS = re.compile(
    r'("(?:password|secret|token|access_token|refresh_token|api_?key|passwd|authorization)":)\s*".*?"',
    re.IGNORECASE,
)
_SKIP_BODY_CONTENT_TYPES = frozenset({
    "multipart/form-data",
    "application/octet-stream",
})

access_logger = logging.getLogger("access")


# ---------------------------------------------------------------------------
# 性能统计
# ---------------------------------------------------------------------------

class PerfStats:
    """内存滚动窗口性能统计。

    每个 API 路径保留最近 N 个请求耗时，支持 p50 / p95 / p99 / avg。
    """

    def __init__(self, window_size: int = PERF_WINDOW_SIZE) -> None:
        self._lock = Lock()
        self._durations: dict[str, deque[float]] = {}
        self._window_size = window_size

    def record(self, path: str, duration_ms: float) -> None:
        """记录一次请求耗时。"""
        # 归一化路径：去掉尾部斜杠，合并动态参数
        normalized = path.rstrip("/") or "/"
        with self._lock:
            if normalized not in self._durations:
                self._durations[normalized] = deque(maxlen=self._window_size)
            self._durations[normalized].append(duration_ms)

    def stats(self, path: str | None = None) -> dict:
        """返回统计数据。

        若不传 path，返回所有端点汇总。
        """
        with self._lock:
            if path:
                deq = self._durations.get(path.rstrip("/"))
                if not deq:
                    return {}
                return self._compute_stats(path, deq)
            result: dict[str, dict] = {}
            for p, deq in sorted(self._durations.items()):
                if deq:
                    result[p] = self._compute_stats(p, deq)
            return result

    def _compute_stats(self, path: str, durations: deque[float]) -> dict:
        sorted_d = sorted(durations)
        n = len(sorted_d)
        return {
            "path": path,
            "count": n,
            "avg_ms": round(sum(sorted_d) / n, 1),
            "p50_ms": round(sorted_d[int(n * 0.5)], 1) if n > 1 else round(sorted_d[0], 1),
            "p95_ms": round(sorted_d[int(n * 0.95)], 1) if n >= 20 else None,
            "p99_ms": round(sorted_d[int(n * 0.99)], 1) if n >= 100 else None,
            "max_ms": round(sorted_d[-1], 1),
            "min_ms": round(sorted_d[0], 1),
        }


# 全局单例（供 system_monitor API 读取）
perf_stats = PerfStats()


# ---------------------------------------------------------------------------
# 中间件
# ---------------------------------------------------------------------------

class RequestLogMiddleware(BaseHTTPMiddleware):
    """记录所有 HTTP 请求到 access log，并注入 X-Request-ID。"""

    async def dispatch(
        self, request: Request, call_next: Any,
    ) -> Response:
        # ---- 1. 请求上下文 ----
        request_id = request.headers.get("X-Request-ID", "")
        set_request_context(request_id=request_id, client_ip=client_ip(request))
        rid = get_request_id()

        # ---- 2. 请求体捕获（可选） ----
        request_body_str: str | None = None
        if request.method.upper() not in ("GET", "HEAD", "DELETE", "OPTIONS"):
            content_type = request.headers.get("content-type", "")
            if not any(ct in content_type for ct in _SKIP_BODY_CONTENT_TYPES):
                try:
                    body_bytes = await request.body()
                    if body_bytes:
                        request_body_str = _sanitize_body(
                            body_bytes.decode("utf-8", errors="replace"))
                except Exception:  # pragma: no cover
                    pass

        # ---- 3. 执行请求 ----
        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        # ---- 4. 响应体捕获（可选） ----
        response_body_str: str | None = None
        response_truncated = False
        content_type = response.headers.get("content-type", "")
        status_code = int(getattr(response, "status_code", 0) or 0)

        should_capture = (
            "json" in content_type
            or "text" in content_type
            or "xml" in content_type
            or status_code >= 400  # 错误始终捕获
        )
        if should_capture and hasattr(response, "body"):
            try:
                body = getattr(response, "body", b"")
                if isinstance(body, bytes) and body:
                    decoded = body.decode("utf-8", errors="replace")
                    if len(decoded) > BODY_MAX_LENGTH:
                        response_body_str = decoded[:BODY_MAX_LENGTH]
                        response_truncated = True
                    else:
                        response_body_str = decoded
                    response_body_str = _sanitize_body(response_body_str)
            except Exception:  # pragma: no cover
                pass

        # ---- 5. 注入 X-Request-ID 到响应头 ----
        if rid:
            try:
                response.headers["X-Request-ID"] = rid
            except Exception:  # headers 可能不可变（如 StreamingResponse）
                pass

        # ---- 6. 写 access log ----
        extra = {
            "method": request.method,
            "path": request.url.path,
            "status": status_code,
            "duration_ms": duration_ms,
            "request_body": request_body_str,
            "response_body": response_body_str,
            "response_body_truncated": response_truncated if response_body_str else None,
        }
        access_logger.info(
            "%s %s %s %sms",
            request.method, request.url.path, status_code, duration_ms,
            extra=extra,
        )

        # ---- 7. 慢请求检测 ----
        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            logging.getLogger(__name__).warning(
                "慢请求: %s %s 耗时 %.0fms（阈值 %dms）",
                request.method, request.url.path, duration_ms,
                SLOW_REQUEST_THRESHOLD_MS,
            )

        # ---- 8. 性能统计 ----
        perf_stats.record(request.url.path, duration_ms)

        return response


# ---------------------------------------------------------------------------
# 脱敏工具
# ---------------------------------------------------------------------------

def _sanitize_body(body: str) -> str:
    """将敏感字段值替换为 ***。"""
    return _SENSITIVE_FIELDS.sub(r'\1"***"', body)
