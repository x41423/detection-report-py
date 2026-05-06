import threading
from app.models.config_model import load_config as _load_config, save_config as _save_config

_config_lock = threading.Lock()


def get_config() -> dict:
    """获取配置（线程安全）"""
    return _load_config()


def update_config(updates: dict) -> dict:
    """更新配置并保存（线程安全）"""
    with _config_lock:
        cfg = _load_config()
        cfg.update(updates)
        _save_config(cfg)
        return cfg


def get_weekly_price_aliases() -> dict[str, str]:
    cfg = get_config()
    aliases = cfg.get("weekly_price_aliases") or {}
    return dict(aliases)


def upsert_weekly_price_aliases(mappings: dict[str, str]) -> dict[str, str]:
    with _config_lock:
        cfg = _load_config()
        aliases = dict(cfg.get("weekly_price_aliases") or {})
        aliases.update(mappings)
        cfg["weekly_price_aliases"] = aliases
        _save_config(cfg)
        return aliases


def delete_weekly_price_alias(source_name: str) -> dict[str, str]:
    with _config_lock:
        cfg = _load_config()
        aliases = dict(cfg.get("weekly_price_aliases") or {})
        aliases.pop(source_name, None)
        cfg["weekly_price_aliases"] = aliases
        _save_config(cfg)
        return aliases
