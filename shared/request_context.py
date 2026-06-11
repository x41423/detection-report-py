"""请求级上下文：request_id / client_ip。

通过 contextvars 在异步请求中安全传递，无需手动传参。
"""

import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_client_ip: ContextVar[str] = ContextVar("client_ip", default="")


def set_request_context(request_id: str = "", client_ip: str = "") -> str:
    """设置当前请求的上下文。返回生成的 request_id。"""
    rid = request_id or str(uuid.uuid4())[:8]
    _request_id.set(rid)
    _client_ip.set(client_ip)
    return rid


def get_request_context() -> dict:
    """返回当前请求上下文，供日志格式化器注入 JSON。"""
    return {
        "request_id": _request_id.get(),
        "client_ip": _client_ip.get(),
    }


def get_request_id() -> str:
    return _request_id.get()
