from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from shared.project_paths import get_project_paths


@dataclass(slots=True)
class AsrShadowCompareRecord:
    request_id: str
    selected_provider: str
    primary_provider: str
    backup_provider: str
    final_provider: str
    fallback_used: bool
    fallback_reason: str
    final_parse_status: str
    primary_duration_ms: int = 0
    backup_duration_ms: int = 0
    primary_quality_status: str = ""
    backup_quality_status: str = ""
    primary_warnings: list[str] = field(default_factory=list)
    backup_warnings: list[str] = field(default_factory=list)
    primary_error: str = ""
    backup_error: str = ""
    primary_transcript: str = ""
    backup_transcript: str = ""
    created_at: str = ""


class AsrShadowCompareStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_project_paths().data_dir / "asr_shadow_compare" / "daily_intake_asr_shadow.jsonl"
        self._lock = threading.Lock()

    def append(self, record: AsrShadowCompareRecord | dict[str, Any]) -> None:
        payload = asdict(record) if isinstance(record, AsrShadowCompareRecord) else dict(record)
        payload.setdefault("created_at", datetime.now().astimezone().isoformat(timespec="seconds"))

        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
                handle.write("\n")

    def read_recent(self, *, limit: int = 50) -> list[dict[str, Any]]:
        normalized_limit = max(1, min(int(limit or 50), 500))
        if not self.path.exists():
            return []

        with self._lock:
            lines = self.path.read_text(encoding="utf-8").splitlines()

        records: list[dict[str, Any]] = []
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
            if len(records) >= normalized_limit:
                break
        return records

    def export_path(self) -> Path:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self.path.write_text("", encoding="utf-8", newline="\n")
            return self.path
