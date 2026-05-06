"""Helpers for extracting audit-relevant metadata from HTTP requests."""

from __future__ import annotations

from starlette.requests import Request


def client_ip(request: Request) -> str:
    """Extract the best-effort client IP, honouring ``X-Forwarded-For``."""

    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else ""


def user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")
