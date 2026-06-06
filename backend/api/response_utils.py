"""Shared response helpers for API endpoints.

Aligns with the existing {success, message, items, total} format used by
InventoryBalanceListResponse and similar endpoints across the codebase.
"""

from __future__ import annotations


def list_response(items: list, total: int, message: str = "") -> dict:
    """Return the standard list-response envelope."""
    return {"success": True, "message": message, "items": items, "total": total}


def mutation_response(message: str, **extra: object) -> dict:
    """Return the standard create/update/delete response envelope."""
    return {"success": True, "message": message, **extra}


def future_endpoint(module: str) -> dict:
    """Convenience dict for endpoints that return HTTP 501.

    Usage in a route::

        raise HTTPException(status_code=501, detail=future_endpoint("delivery_tasks"))
    """
    return {"future": True, "module": module, "message": f"{module} 功能规划中"}
