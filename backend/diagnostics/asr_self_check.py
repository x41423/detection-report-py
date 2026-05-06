"""Startup self-check for the ASR provider stack.

Verifies that the three Python modules we recovered from ``.pyc`` (Qwen3-ASR
provider, faster-whisper provider, and the daily-intake ASR orchestrator) are
loaded from the expected paths with full source, not from leftover stubs.

The check is intentionally defensive:

* Every module must live under ``backend/services/`` (or ``backend/funasr_lab/``
  for the lab service). A module imported from ``.runtime/`` or any other
  location is treated as an accidental stub.
* The source file must be larger than the historical stub size (~350 bytes);
  we require >1500 bytes.
* The source must not contain the ``_STUB_REASON`` / "尚未恢复" / "原文件被清空"
  strings that only existed in the placeholder files.
* For the two providers we instantiate the class and call
  :meth:`is_dependency_available`, collecting missing runtime dependencies
  without failing the report (they are environment-specific).

The result is a plain ``dict`` shaped like::

    {
        "ok": bool,
        "modules": [
            {"name": ..., "file": ..., "size": int, "ok": bool, "issue": str | None},
            ...
        ],
        "providers": [
            {"name": ..., "available": bool, "error": str | None},
            ...
        ],
        "warnings": [str, ...],
    }

When ``strict=True`` any failure raises :class:`RuntimeError` with the first
warning so startup scripts can exit non-zero.
"""

from __future__ import annotations

import importlib
import inspect
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_SERVICES_DIR = _BACKEND_ROOT / "services"
_FUNASR_DIR = _BACKEND_ROOT / "funasr_lab"

_MIN_SOURCE_BYTES = 1500
_STUB_NEEDLES: tuple[str, ...] = (
    "_STUB_REASON",
    "尚未恢复",
    "原文件被清空",
    "缓存的 .pyc",
)


@dataclass(slots=True)
class _ModuleSpec:
    name: str
    expected_dir: Path


_MODULES: tuple[_ModuleSpec, ...] = (
    _ModuleSpec("backend.services.qwen3_asr_provider", _SERVICES_DIR),
    _ModuleSpec("backend.services.speech_to_text_service", _SERVICES_DIR),
    _ModuleSpec("backend.services.daily_intake_asr_service", _SERVICES_DIR),
    _ModuleSpec("backend.funasr_lab.service", _FUNASR_DIR),
)


def _check_module(spec: _ModuleSpec) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": spec.name,
        "file": None,
        "size": 0,
        "ok": False,
        "issue": None,
    }
    try:
        importlib.invalidate_caches()
        module = importlib.import_module(spec.name)
    except Exception as exc:  # pragma: no cover - environmental
        entry["issue"] = f"import failed: {exc!r}"
        return entry

    module_file = getattr(module, "__file__", None)
    if not module_file:
        entry["issue"] = "module has no __file__"
        return entry

    file_path = Path(module_file).resolve()
    entry["file"] = str(file_path)

    try:
        entry["size"] = file_path.stat().st_size
    except OSError as exc:
        entry["issue"] = f"cannot stat source: {exc!r}"
        return entry

    try:
        expected_dir = spec.expected_dir.resolve()
    except OSError:
        expected_dir = spec.expected_dir

    try:
        file_path.relative_to(expected_dir)
    except ValueError:
        entry["issue"] = (
            f"module loaded from unexpected location (expected under {expected_dir})"
        )
        return entry

    if entry["size"] < _MIN_SOURCE_BYTES:
        entry["issue"] = (
            f"source too small ({entry['size']} bytes < {_MIN_SOURCE_BYTES})"
            " — stub source suspected"
        )
        return entry

    try:
        source = inspect.getsource(module)
    except OSError as exc:
        entry["issue"] = f"cannot read source: {exc!r}"
        return entry

    for needle in _STUB_NEEDLES:
        if needle in source:
            entry["issue"] = f"stub marker '{needle}' present in source"
            return entry

    entry["ok"] = True
    return entry


def _check_provider(class_path: str, display_name: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": display_name,
        "available": False,
        "error": None,
    }
    module_name, _, class_name = class_path.rpartition(".")
    try:
        module = importlib.import_module(module_name)
        provider_cls = getattr(module, class_name)
    except Exception as exc:
        entry["error"] = f"cannot load {class_path}: {exc!r}"
        return entry

    try:
        provider = provider_cls()
    except Exception as exc:
        entry["error"] = f"instantiation failed: {exc!r}"
        return entry

    try:
        entry["available"] = bool(provider.is_dependency_available())
    except Exception as exc:
        entry["error"] = f"dependency probe failed: {exc!r}"
    return entry


def run_asr_self_check(strict: bool = False) -> dict[str, Any]:
    """Run the full self-check and return a structured report.

    Args:
        strict: If true, raise :class:`RuntimeError` for any failure so that
            CLI callers can exit non-zero.
    """

    module_reports: list[dict[str, Any]] = [_check_module(spec) for spec in _MODULES]
    provider_reports: list[dict[str, Any]] = [
        _check_provider(
            "backend.services.qwen3_asr_provider.Qwen3AsrProvider",
            "qwen3-asr",
        ),
        _check_provider(
            "backend.services.speech_to_text_service.SpeechToTextService",
            "faster-whisper",
        ),
    ]

    warnings: list[str] = []
    for entry in module_reports:
        if not entry["ok"]:
            warnings.append(f"module {entry['name']}: {entry['issue']}")
    # Providers are allowed to report unavailable dependencies without failing
    # the overall check, but hard loader errors (``error`` set) are fatal.
    for entry in provider_reports:
        if entry["error"]:
            warnings.append(f"provider {entry['name']}: {entry['error']}")

    ok = not warnings
    report = {
        "ok": ok,
        "modules": module_reports,
        "providers": provider_reports,
        "warnings": warnings,
    }

    if strict and not ok:
        raise RuntimeError(f"ASR self-check failed: {warnings[0]}")

    return report
