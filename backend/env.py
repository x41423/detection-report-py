from __future__ import annotations

import os
from pathlib import Path

from shared.project_paths import get_project_paths
ROOT_DIR = get_project_paths().root


def load_project_env() -> None:
    original_env_keys = set(os.environ.keys())

    _load_env_file(ROOT_DIR / ".env", original_env_keys)
    _load_env_file(ROOT_DIR / ".env.local", original_env_keys)


def _load_env_file(path: Path, original_env_keys: set[str]) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        env_key = key.strip()
        if not env_key or env_key in original_env_keys:
            continue

        env_value = _strip_wrapping_quotes(value.strip())
        os.environ[env_key] = env_value


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
