"""JSON 行日志格式化器。

配合 RotatingFileHandler 使用，输出每行一个 JSON 对象。
自动注入请求上下文（request_id / client_ip）。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta

# 北京时间 (UTC+8)
_BEIJING_TZ = timezone(timedelta(hours=8))


class JsonLineFormatter(logging.Formatter):
    """将日志记录格式化为单行 JSON（北京时间 UTC+8）。

    示例输出:
    {"time":"2026-06-10T19:30:00.123+08:00","level":"INFO","logger":"backend.main",
     "message":"Server started","module":"main:lifespan:77","request_id":"a3f8c2e1"}
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "time": datetime.now(_BEIJING_TZ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": f"{record.module}:{record.funcName}:{record.lineno}",
        }

        # 注入请求上下文
        try:
            from shared.request_context import get_request_context  # noqa: PLC0415
        except ImportError:  # pragma: no cover — 桌面端已移除，仅防御
            pass
        else:
            ctx = get_request_context()
            if ctx.get("request_id"):
                entry["request_id"] = ctx["request_id"]
            if ctx.get("client_ip"):
                entry["client_ip"] = ctx["client_ip"]

        # 异常信息
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])

        # 附加字段（access log 中间件通过 extra= 传入）
        for attr in ("method", "path", "status", "duration_ms",
                     "request_body", "response_body", "response_body_truncated"):
            value = getattr(record, attr, None)
            if value is not None:
                entry[attr] = value

        return json.dumps(entry, ensure_ascii=False, default=str)
