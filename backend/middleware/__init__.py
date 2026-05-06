"""HTTP middleware shared across the backend API."""

from backend.middleware.audit_middleware import AuditMiddleware

__all__ = ["AuditMiddleware"]
