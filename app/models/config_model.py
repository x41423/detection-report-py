import copy
import json
from pathlib import Path

from app.utils.weekly_price_update import get_default_weekly_price_aliases
from shared.project_paths import get_project_paths


def _get_defaults_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "defaults.json"


def _load_defaults() -> dict:
    path = _get_defaults_path()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {}
    cfg.setdefault("weekly_price_aliases", get_default_weekly_price_aliases())
    return cfg


def _default_config() -> dict:
    """Lazy-loaded default config, cached after first call."""
    return _load_defaults()


def get_config_path() -> str:
    return str(get_project_paths().config_file)


def get_legacy_config_path() -> str:
    return str(get_project_paths().legacy_root_config_file)


def resolve_read_config_path() -> Path:
    paths = get_project_paths()
    if paths.config_file.exists():
        return paths.config_file
    if paths.legacy_root_config_file.exists():
        return paths.legacy_root_config_file
    return paths.config_file


def _merge_and_remove_legacy(cfg: dict):
    """If legacy root config.json exists, merge its unique keys into canonical config/app.json and rename legacy to .bak."""
    paths = get_project_paths()
    legacy = paths.legacy_root_config_file
    canonical = paths.config_file
    if not legacy.exists() or legacy == canonical:
        return
    try:
        with legacy.open("r", encoding="utf-8") as f:
            legacy_cfg = json.load(f)
    except Exception:
        return
    changed = False
    for k, v in legacy_cfg.items():
        if k not in cfg:
            cfg[k] = v
            changed = True
    if changed:
        canonical.parent.mkdir(parents=True, exist_ok=True)
        with canonical.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    bak = legacy.with_suffix(".merged.bak")
    legacy.rename(bak)
    print(f"[CONFIG] 已合并 legacy config.json → {bak}")


def load_config() -> dict:
    path = resolve_read_config_path()
    canonical_path = Path(get_config_path())
    defaults = _default_config()

    if not path.exists():
        save_config(defaults)
        return copy.deepcopy(defaults)

    try:
        with path.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    changed = False
    for k, v in defaults.items():
        if k not in cfg:
            cfg[k] = copy.deepcopy(v)
            changed = True

    if changed or path != canonical_path:
        save_config(cfg)

    # Merge legacy root config.json if it still exists
    _merge_and_remove_legacy(cfg)

    return cfg


def save_config(cfg: dict):
    path = Path(get_config_path())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")
