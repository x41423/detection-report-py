from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shared.project_paths import get_project_paths


@dataclass(frozen=True, slots=True)
class AsrCorrectionEntry:
    alias: str
    canonical_name: str
    unit: str
    status: str
    use_count: int = 1


class AsrCorrectionLexicon:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_project_paths().data_dir / "asr_corrections" / "funasr_lab_corrections.json"

    def load_entries(self, *, statuses: set[str] | None = None) -> list[AsrCorrectionEntry]:
        expected_statuses = statuses or {"active"}
        raw_store = self._read_store()
        entries: list[AsrCorrectionEntry] = []
        seen_keys: set[tuple[str, str, str]] = set()

        for item in raw_store.get("entries") or []:
            entry = self._normalize_entry(item)
            if entry is None or entry.status not in expected_statuses:
                continue
            key = (entry.alias.lower(), entry.canonical_name.lower(), entry.unit.lower())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            entries.append(entry)

        entries.sort(key=lambda entry: entry.use_count, reverse=True)
        return entries

    def _read_store(self) -> dict[str, Any]:
        try:
            return json.loads(Path(self.path).read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _normalize_entry(self, raw_item: Any) -> AsrCorrectionEntry | None:
        item = raw_item if isinstance(raw_item, dict) else {}
        alias = self._normalize_term(item.get("alias"))
        canonical_name = self._normalize_term(item.get("canonical_name"))
        unit = self._normalize_term(item.get("unit"))
        status = str(item.get("status") or "").strip().lower()
        if not alias or not canonical_name or not unit or not status:
            return None
        try:
            use_count = max(int(item.get("use_count") or 1), 1)
        except (TypeError, ValueError):
            use_count = 1
        return AsrCorrectionEntry(
            alias=alias,
            canonical_name=canonical_name,
            unit=unit,
            status=status,
            use_count=use_count,
        )

    def _normalize_term(self, raw_value: Any) -> str:
        value = str(raw_value or "").strip()
        if any(marker in value for marker in ("\r", "\n", "\t")):
            value = " ".join(value.split())
        if not value or len(value) > 64:
            return ""
        if any(marker in value for marker in ("\\", "/")):
            return ""
        return value
