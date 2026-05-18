"""Bind inspector_name to authenticated user identity for report traceability."""


def get_inspector_name(context=None) -> str:
    """Get inspector name — prefers logged-in user's display_name, falls back to config.

    Args:
        context: Optional AuthContext from get_current_auth_context() FastAPI dependency.
    """
    if context is not None and hasattr(context, "user"):
        user = context.user
        if hasattr(user, "display_name") and user.display_name:
            return user.display_name

    from backend.services.config_service import get_config

    cfg = get_config()
    return cfg.get("inspector_name", "检测员")


def get_inspector_user_id(context=None) -> str | None:
    """Get the user_id of the current inspector for audit logging.

    Args:
        context: Optional AuthContext from get_current_auth_context() FastAPI dependency.
    """
    if context is not None and hasattr(context, "user"):
        user = context.user
        if hasattr(user, "id"):
            return str(user.id)
    return None
