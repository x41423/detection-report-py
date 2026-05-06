from __future__ import annotations

import os
from http.cookies import SimpleCookie

from fastapi import Response


AUTH_COOKIE_PATH = "/api/auth"
DEFAULT_REFRESH_COOKIE_NAME = "auth_refresh_token"
DEFAULT_COOKIE_SAMESITE = "lax"


def refresh_cookie_name() -> str:
    return (os.getenv("AUTH_REFRESH_COOKIE_NAME", DEFAULT_REFRESH_COOKIE_NAME) or DEFAULT_REFRESH_COOKIE_NAME).strip()


def refresh_cookie_secure() -> bool:
    raw_value = os.getenv("AUTH_COOKIE_SECURE", "false")
    return str(raw_value or "").strip().lower() in {"1", "true", "yes", "on"}


def refresh_cookie_samesite() -> str:
    raw_value = (os.getenv("AUTH_COOKIE_SAMESITE", DEFAULT_COOKIE_SAMESITE) or DEFAULT_COOKIE_SAMESITE).strip().lower()
    if raw_value in {"lax", "strict", "none"}:
        return raw_value
    return DEFAULT_COOKIE_SAMESITE


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=refresh_cookie_name(),
        value=refresh_token,
        httponly=True,
        secure=refresh_cookie_secure(),
        samesite=refresh_cookie_samesite(),
        path=AUTH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=refresh_cookie_name(),
        path=AUTH_COOKIE_PATH,
        secure=refresh_cookie_secure(),
        httponly=True,
        samesite=refresh_cookie_samesite(),
    )


def clear_refresh_cookie_header() -> str:
    cookie = SimpleCookie()
    cookie[refresh_cookie_name()] = ""
    morsel = cookie[refresh_cookie_name()]
    morsel["path"] = AUTH_COOKIE_PATH
    morsel["max-age"] = 0
    morsel["httponly"] = True
    morsel["samesite"] = refresh_cookie_samesite()
    if refresh_cookie_secure():
        morsel["secure"] = True
    return morsel.OutputString()
