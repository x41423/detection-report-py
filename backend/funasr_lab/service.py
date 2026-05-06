"""FunASR Lab service: isolated Qwen3-ASR test flow with lexicon lifecycle.

The service is intentionally self-contained:

* It stores correction candidates in ``data/asr_corrections/funasr_lab_corrections.json``.
* It persists recent hotwords / name-unit memory and daily tracking entries
  inside the main ``config.json`` so the main Daily Intake page can share
  lexicon knowledge when enabled.
* It delegates the actual audio transcription to the production
  :class:`Qwen3AsrProvider` – the lab only owns the prompt building, memory
  bookkeeping and tracking persistence.
"""
from __future__ import annotations

import copy
import importlib
import importlib.metadata
import importlib.util
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.models.config_model import load_config, save_config
from backend.env import get_project_paths
from backend.services.asr_provider import (
    AsrProviderUnavailableError,
    AsrTranscriptionResult,
)
from backend.services.qwen3_asr_provider import (
    QWEN_ASR_MODEL_TAG,
    Qwen3AsrProvider,
)


_logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "Qwen/Qwen3-ASR-1.7B"
_DEFAULT_LANGUAGE = "Chinese"
_DEFAULT_DEVICE = "auto"
_DEFAULT_MAX_NEW_TOKENS = 256

_CORRECTION_STORE_RELATIVE = Path("data") / "asr_corrections" / "funasr_lab_corrections.json"
_AUDIO_RETENTION_RELATIVE = Path("data") / "asr_corrections" / "audio"
_TRAINING_EXPORT_RELATIVE = Path("data") / "asr_corrections"
_MANUAL_HOTWORDS_RELATIVE = Path("config") / "funasr_lab_hotwords.jsonc"

_TRACKING_CONFIG_KEY = "funasr_lab_daily_tracking"
_MEMORY_CONFIG_KEY = "funasr_lab_memory"

_RECENT_HOTWORDS_LIMIT = 80
_NAME_UNIT_MEMORY_LIMIT = 200


class FunASRLabError(RuntimeError):
    """Raised when the lab cannot satisfy a request (validation / lifecycle)."""


@dataclass(slots=True)
class FunASRLabConfig:
    model: str = _DEFAULT_MODEL
    device: str = _DEFAULT_DEVICE
    language: str = _DEFAULT_LANGUAGE
    max_new_tokens: int = _DEFAULT_MAX_NEW_TOKENS
    use_domain_context: bool = True
    extra_context: str | None = None
    compare_with_baseline: bool = False
    parse_daily_intake: bool = False
    retain_training_audio: bool = False
    intake_date: str | None = None
    category: str | None = None


class FunASRLabService:
    """Facade used by ``/api/test/funasr-lab/*`` endpoints."""

    def __init__(
        self,
        *,
        qwen_provider: Qwen3AsrProvider | None = None,
    ) -> None:
        paths = get_project_paths()
        root: Path = paths.root
        self.correction_store_path: Path = root / _CORRECTION_STORE_RELATIVE
        self.audio_retention_dir: Path = root / _AUDIO_RETENTION_RELATIVE
        self.training_export_dir: Path = root / _TRAINING_EXPORT_RELATIVE
        self.manual_hotword_config_path: Path = root / _MANUAL_HOTWORDS_RELATIVE

        self._qwen_provider = qwen_provider or Qwen3AsrProvider()
        self._model_cache: dict[tuple[str, str], Any] = {}

    # ------------------------------------------------------------------
    # Dependency / status
    # ------------------------------------------------------------------
    def is_dependency_available(self) -> bool:
        return self._qwen_provider.is_dependency_available()

    def status(self) -> dict[str, Any]:
        dependency_available = self.is_dependency_available()
        return {
            "success": True,
            "provider": "qwen3-asr",
            "available": dependency_available,
            "message": self._qwen_provider.readiness_message(),
            "defaults": {
                "model": _DEFAULT_MODEL,
                "device": _DEFAULT_DEVICE,
                "language": _DEFAULT_LANGUAGE,
                "max_new_tokens": _DEFAULT_MAX_NEW_TOKENS,
            },
            "qwen": {
                "has_transformers": importlib.util.find_spec("transformers") is not None,
                "transformers_version": self._safe_version("transformers"),
            },
            "stub": False,
        }

    @staticmethod
    def _safe_version(package: str) -> str | None:
        try:
            return importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Daily tracking
    # ------------------------------------------------------------------
    def tracking_status(
        self,
        *,
        intake_date: str | None = None,
        days: int = 7,
    ) -> dict[str, Any]:
        cfg = load_config() or {}
        tracking = (cfg.get(_TRACKING_CONFIG_KEY) or {}).get("records") or {}
        selected_date = (intake_date or "").strip() or self._today_str()
        selected_items = list(tracking.get(selected_date) or [])

        recent_days = self._collect_recent_days(tracking, reference_date=selected_date, days=max(1, int(days)))
        return {
            "success": True,
            "intake_date": selected_date,
            "days": days,
            "entries": selected_items,
            "selected_day": self._summarize_day(selected_date, selected_items),
            "recent_days": recent_days,
            "message": "",
        }

    def record_tracking_entry(
        self,
        *,
        intake_date: str,
        raw_name: str,
        normalized_name: str,
        unit: str,
        quantity: float,
        category: str | None = None,
        transcript: str | None = None,
        source: str = "funasr-lab",
    ) -> dict[str, Any]:
        date_key = (intake_date or "").strip() or self._today_str()
        canonical_name = (normalized_name or "").strip() or (raw_name or "").strip()
        unit_value = (unit or "").strip()
        if not canonical_name:
            raise FunASRLabError("normalized_name 或 raw_name 必须提供一个非空值。")
        try:
            quantity_value = float(quantity)
        except (TypeError, ValueError) as exc:
            raise FunASRLabError(f"quantity 必须是数字：{quantity!r}") from exc

        cfg = load_config() or {}
        tracking_root = copy.deepcopy(cfg.get(_TRACKING_CONFIG_KEY) or {})
        records: dict[str, list[dict[str, Any]]] = dict(tracking_root.get("records") or {})
        day_items = list(records.get(date_key) or [])

        merged = False
        now_iso = self._now_iso()
        for item in day_items:
            if (
                (item.get("normalized_name") or "").strip() == canonical_name
                and (item.get("unit") or "").strip() == unit_value
            ):
                try:
                    existing_qty = float(item.get("quantity") or 0)
                except (TypeError, ValueError):
                    existing_qty = 0.0
                item["quantity"] = round(existing_qty + quantity_value, 4)
                item["merge_count"] = int(item.get("merge_count") or 1) + 1
                item["updated_at"] = now_iso
                if transcript:
                    item["transcript"] = transcript
                if category:
                    item["category"] = category
                merged = True
                break

        if not merged:
            day_items.append(
                {
                    "id": self._new_id("track"),
                    "raw_name": (raw_name or "").strip(),
                    "normalized_name": canonical_name,
                    "unit": unit_value,
                    "quantity": round(quantity_value, 4),
                    "category": (category or "").strip(),
                    "transcript": (transcript or "").strip(),
                    "source": source or "funasr-lab",
                    "merge_count": 1,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }
            )

        records[date_key] = day_items
        tracking_root["records"] = records
        cfg[_TRACKING_CONFIG_KEY] = tracking_root
        save_config(cfg)

        return {
            "success": True,
            "merged": merged,
            "message": "Merged with existing entry." if merged else "Added to today's tracking.",
            "selected_day": self._summarize_day(date_key, day_items),
            "recent_days": self._collect_recent_days(records, reference_date=date_key, days=7),
        }

    def _summarize_day(self, date_key: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        unique_names: set[str] = set()
        total_quantity = 0.0
        merge_event_count = 0
        for item in items:
            name = (item.get("normalized_name") or item.get("raw_name") or "").strip()
            if name:
                unique_names.add(name)
            try:
                total_quantity += float(item.get("quantity") or 0)
            except (TypeError, ValueError):
                pass
            merge_event_count += int(item.get("merge_count") or 1)
        return {
            "intake_date": date_key,
            "total_count": len(items),
            "unique_name_count": len(unique_names),
            "total_quantity": round(total_quantity, 4),
            "merge_event_count": merge_event_count,
            "items": items,
        }

    def _collect_recent_days(
        self,
        tracking: dict[str, list[dict[str, Any]]],
        *,
        reference_date: str,
        days: int,
    ) -> list[dict[str, Any]]:
        try:
            anchor = datetime.strptime(reference_date, "%Y-%m-%d").date()
        except Exception:
            anchor = datetime.utcnow().date()
        out: list[dict[str, Any]] = []
        for offset in range(days):
            day = anchor - timedelta(days=offset)
            key = day.strftime("%Y-%m-%d")
            items = list(tracking.get(key) or [])
            out.append(self._summarize_day(key, items))
        return out

    # ------------------------------------------------------------------
    # Lab memory + manual hotwords
    # ------------------------------------------------------------------
    def _load_lab_memory(self) -> dict[str, Any]:
        cfg = load_config() or {}
        memory = copy.deepcopy(cfg.get(_MEMORY_CONFIG_KEY) or {})
        memory.setdefault("recent_hotwords", [])
        memory.setdefault("name_unit_memory", [])
        return memory

    def _save_lab_memory(self, memory: dict[str, Any]) -> None:
        cfg = load_config() or {}
        cfg[_MEMORY_CONFIG_KEY] = memory
        save_config(cfg)

    def _load_manual_hotword_config(self) -> dict[str, Any]:
        path = self.manual_hotword_config_path
        fallback = {"manual_hotwords": [], "name_unit_memory": [], "path": str(path)}
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except (OSError, ValueError):
            return fallback
        try:
            data = self._parse_jsonc(raw)
        except Exception as exc:
            _logger.warning("Failed to parse manual hotword config %s: %s", path, exc)
            return fallback
        if not isinstance(data, dict):
            return fallback
        manual_hotwords = [
            str(x).strip()
            for x in (data.get("manual_hotwords") or [])
            if str(x).strip()
        ]
        name_unit_memory = [
            item
            for item in (data.get("name_unit_memory") or [])
            if isinstance(item, dict) and item.get("alias") and item.get("canonical_name")
        ]
        return {
            "manual_hotwords": manual_hotwords,
            "name_unit_memory": name_unit_memory,
            "path": str(path),
        }

    @staticmethod
    def _parse_jsonc(text: str) -> Any:
        # Strip // line comments and /* ... */ block comments while keeping
        # string literals intact.
        def _strip_line_comments(source: str) -> str:
            result: list[str] = []
            in_string = False
            string_char = ""
            i = 0
            while i < len(source):
                ch = source[i]
                if in_string:
                    result.append(ch)
                    if ch == "\\" and i + 1 < len(source):
                        result.append(source[i + 1])
                        i += 2
                        continue
                    if ch == string_char:
                        in_string = False
                    i += 1
                    continue
                if ch in ("\"", "'"):
                    in_string = True
                    string_char = ch
                    result.append(ch)
                    i += 1
                    continue
                if ch == "/" and i + 1 < len(source):
                    nxt = source[i + 1]
                    if nxt == "/":
                        newline = source.find("\n", i)
                        i = len(source) if newline == -1 else newline
                        continue
                    if nxt == "*":
                        end = source.find("*/", i + 2)
                        i = len(source) if end == -1 else end + 2
                        continue
                result.append(ch)
                i += 1
            return "".join(result)

        cleaned = _strip_line_comments(text)
        # Also tolerate trailing commas.
        cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
        return json.loads(cleaned)

    def _remember_recent_usage(
        self,
        *,
        user_hotword: str | None,
        parse_payload: dict[str, Any] | None,
    ) -> None:
        """Persist the user-supplied hotword (if any) to the lab memory.

        Parse-derived name/unit pairs are *not* promoted into memory here –
        they follow the explicit correction-candidate lifecycle and must be
        confirmed by the operator before influencing future prompts.
        """
        hotword = (user_hotword or "").strip()
        if not hotword:
            return
        memory = self._load_lab_memory()
        recent = [str(x).strip() for x in (memory.get("recent_hotwords") or []) if str(x).strip()]
        if hotword in recent:
            recent.remove(hotword)
        recent.insert(0, hotword)
        memory["recent_hotwords"] = recent[:_RECENT_HOTWORDS_LIMIT]
        self._save_lab_memory(memory)

    # ------------------------------------------------------------------
    # Context prompt
    # ------------------------------------------------------------------
    def _build_context_prompt(self, config: FunASRLabConfig) -> str:
        if not config.use_domain_context:
            # Even when domain context is disabled we still honour
            # extra_context because it represents operator intent (e.g.
            # "today's supplier is A").
            return (config.extra_context or "").strip()

        sections: list[str] = [
            "This is a food inventory or daily-intake audio clip in Chinese.",
            "Focus on ingredient names, quantities and units.",
            "Prefer Arabic numerals and decimal points (for example 4.8斤 not 4斤8斤).",
        ]

        memory = self._load_lab_memory()
        manual = self._load_manual_hotword_config()

        hotwords = self._merge_unique(
            list(memory.get("recent_hotwords") or []),
            list(manual.get("manual_hotwords") or []),
        )
        if hotwords:
            sections.append("Recent / manual hotwords: " + ", ".join(hotwords) + ".")

        memory_pairs = self._format_name_unit_pairs(memory.get("name_unit_memory") or [])
        manual_pairs = self._format_name_unit_pairs(manual.get("name_unit_memory") or [])
        pairs = self._merge_unique(memory_pairs, manual_pairs)
        if pairs:
            sections.append("Known name/unit pairs: " + "; ".join(pairs) + ".")

        active_pairs = self._format_name_unit_pairs(self._load_active_correction_pairs())
        if active_pairs:
            sections.append("Confirmed correction pairs: " + "; ".join(active_pairs) + ".")

        extra = (config.extra_context or "").strip()
        if extra:
            sections.append(extra)

        return "\n".join(sections)

    @staticmethod
    def _merge_unique(*lists: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for candidate_list in lists:
            for item in candidate_list:
                key = str(item or "").strip()
                if not key or key in seen:
                    continue
                seen.add(key)
                out.append(key)
        return out

    @staticmethod
    def _format_name_unit_pairs(entries: list[dict[str, Any]]) -> list[str]:
        out: list[str] = []
        for entry in entries:
            alias = str(entry.get("alias") or "").strip()
            canonical = str(entry.get("canonical_name") or "").strip()
            unit = str(entry.get("unit") or "").strip()
            if not alias or not canonical:
                continue
            pair = f"{alias} -> {canonical}"
            if unit:
                pair += f" ({unit})"
            out.append(pair)
        return out

    def _load_active_correction_pairs(self) -> list[dict[str, Any]]:
        store = self._load_correction_store()
        result = []
        for entry in store.get("entries") or []:
            if entry.get("status") == "active":
                result.append(
                    {
                        "alias": entry.get("alias"),
                        "canonical_name": entry.get("canonical_name"),
                        "unit": entry.get("unit"),
                    }
                )
        return result

    # ------------------------------------------------------------------
    # Correction store (file-backed)
    # ------------------------------------------------------------------
    def _load_correction_store(self) -> dict[str, Any]:
        path = self.correction_store_path
        try:
            raw = Path(path).read_text(encoding="utf-8")
        except (OSError, ValueError):
            return {"lexicon_version": 0, "entries": []}
        try:
            data = json.loads(raw)
        except Exception:
            return {"lexicon_version": 0, "entries": []}
        if not isinstance(data, dict):
            return {"lexicon_version": 0, "entries": []}
        data.setdefault("lexicon_version", 0)
        data.setdefault("entries", [])
        return data

    def _save_correction_store(self, store: dict[str, Any]) -> None:
        path = Path(self.correction_store_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(store, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def lexicon_status(self, *, include_entries: bool = True) -> dict[str, Any]:
        store = self._load_correction_store()
        entries = list(store.get("entries") or [])
        counts = {status: 0 for status in ("pending", "confirmed", "active", "disabled", "exported")}
        for entry in entries:
            status = str(entry.get("status") or "")
            if status in counts:
                counts[status] += 1
            if entry.get("exported_at"):
                counts["exported"] = counts.get("exported", 0) + (0 if status == "exported" else 1)
        # Exported is tracked via timestamp rather than status; recompute from scratch.
        counts["exported"] = sum(1 for e in entries if e.get("exported_at"))
        candidates = [e for e in entries if e.get("status") == "pending"]
        return {
            "success": True,
            "lexicon_version": int(store.get("lexicon_version") or 0),
            "counts": counts,
            "include_entries": include_entries,
            "entries": entries if include_entries else [],
            "candidates": candidates,
            "message": "",
        }

    def create_lexicon_candidate(
        self,
        *,
        alias: str,
        canonical_name: str,
        unit: str,
        raw_transcript: str | None = None,
        corrected_transcript: str | None = None,
        source: str = "qwen3-asr-lab",
    ) -> dict[str, Any]:
        alias = (alias or "").strip()
        canonical_name = (canonical_name or "").strip()
        unit = (unit or "").strip()
        if not alias or not canonical_name:
            raise FunASRLabError("alias 与 canonical_name 都必须为非空字符串。")
        if alias == canonical_name and not unit:
            raise FunASRLabError("alias == canonical_name 时必须提供 unit。")

        store = self._load_correction_store()
        now_iso = self._now_iso()
        entry = {
            "id": self._new_id("corr"),
            "alias": alias,
            "canonical_name": canonical_name,
            "unit": unit,
            "status": "pending",
            "source": source or "qwen3-asr-lab",
            "raw_transcript": (raw_transcript or "").strip(),
            "corrected_transcript": (corrected_transcript or "").strip(),
            "created_at": now_iso,
            "updated_at": now_iso,
            "confirmed_at": None,
            "activated_at": None,
            "disabled_at": None,
            "disable_reason": None,
            "exported_at": None,
            "audio_ref": None,
            "audio_content_type": None,
        }
        entries = list(store.get("entries") or [])
        entries.append(entry)
        store["entries"] = entries
        self._save_correction_store(store)
        return {
            "success": True,
            "message": "Correction candidate added as pending.",
            "entry": entry,
            "lexicon_version": int(store.get("lexicon_version") or 0),
        }

    def confirm_lexicon_entries(self, *, ids: list[str]) -> dict[str, Any]:
        if not ids:
            raise FunASRLabError("ids 不能为空。")
        store = self._load_correction_store()
        entries = list(store.get("entries") or [])
        id_set = {str(x).strip() for x in ids if str(x).strip()}
        confirmed = 0
        now_iso = self._now_iso()
        for entry in entries:
            if entry.get("id") in id_set and entry.get("status") == "pending":
                entry["status"] = "confirmed"
                entry["confirmed_at"] = now_iso
                entry["updated_at"] = now_iso
                confirmed += 1
        store["entries"] = entries
        self._save_correction_store(store)
        return {
            "success": True,
            "confirmed_total": confirmed,
            "lexicon_version": int(store.get("lexicon_version") or 0),
            "message": f"Confirmed {confirmed} correction(s).",
        }

    def apply_incremental_lexicon(
        self,
        *,
        scope: str = "all_confirmed",
        ids: list[str] | None = None,
    ) -> dict[str, Any]:
        normalized_scope = (scope or "all_confirmed").strip() or "all_confirmed"
        if normalized_scope not in {"all_confirmed", "selected"}:
            raise FunASRLabError(f"unknown scope: {scope!r}")

        store = self._load_correction_store()
        entries = list(store.get("entries") or [])
        id_set = {str(x).strip() for x in (ids or []) if str(x).strip()}
        now_iso = self._now_iso()
        activated = 0
        for entry in entries:
            if entry.get("status") != "confirmed":
                continue
            if normalized_scope == "selected" and entry.get("id") not in id_set:
                continue
            entry["status"] = "active"
            entry["activated_at"] = now_iso
            entry["updated_at"] = now_iso
            activated += 1

        if activated > 0:
            store["lexicon_version"] = int(store.get("lexicon_version") or 0) + 1
            store["entries"] = entries
            self._save_correction_store(store)

        effective_pairs = sum(1 for e in entries if e.get("status") == "active")
        return {
            "success": True,
            "activated_total": activated,
            "effective_pair_total": effective_pairs,
            "lexicon_version": int(store.get("lexicon_version") or 0),
            "message": f"Activated {activated} correction(s).",
        }

    def disable_lexicon_entries(
        self,
        *,
        ids: list[str],
        reason: str | None = None,
    ) -> dict[str, Any]:
        if not ids:
            raise FunASRLabError("ids 不能为空。")
        store = self._load_correction_store()
        entries = list(store.get("entries") or [])
        id_set = {str(x).strip() for x in ids if str(x).strip()}
        now_iso = self._now_iso()
        disabled = 0
        for entry in entries:
            if entry.get("id") in id_set and entry.get("status") != "disabled":
                entry["status"] = "disabled"
                entry["disabled_at"] = now_iso
                entry["disable_reason"] = (reason or "").strip() or None
                entry["updated_at"] = now_iso
                disabled += 1
        if disabled > 0:
            store["lexicon_version"] = int(store.get("lexicon_version") or 0) + 1
        store["entries"] = entries
        self._save_correction_store(store)
        return {
            "success": True,
            "disabled_total": disabled,
            "lexicon_version": int(store.get("lexicon_version") or 0),
            "message": f"Disabled {disabled} correction(s).",
        }

    def export_lexicon_training_pack(
        self,
        *,
        statuses: list[str] | None = None,
        ids: list[str] | None = None,
    ) -> dict[str, Any]:
        store = self._load_correction_store()
        entries = list(store.get("entries") or [])
        status_set = {
            str(s).strip()
            for s in (statuses or ["confirmed", "active"])
            if str(s).strip()
        }
        id_set = {str(x).strip() for x in (ids or []) if str(x).strip()}

        selected: list[dict[str, Any]] = []
        for entry in entries:
            if entry.get("status") not in status_set:
                continue
            if id_set and entry.get("id") not in id_set:
                continue
            selected.append(entry)

        export_dir = Path(self.training_export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"qwen3-asr-corrections-{timestamp}.jsonl"
        out_path = export_dir / filename

        now_iso = self._now_iso()
        with out_path.open("w", encoding="utf-8") as fh:
            for entry in selected:
                record = {
                    "id": entry.get("id"),
                    "alias": entry.get("alias"),
                    "canonical_name": entry.get("canonical_name"),
                    "unit": entry.get("unit"),
                    "status": entry.get("status"),
                    "raw_transcript": entry.get("raw_transcript") or "",
                    "corrected_transcript": entry.get("corrected_transcript") or "",
                    "exported_at": now_iso,
                }
                audio_ref = entry.get("audio_ref")
                if audio_ref:
                    record["audio_ref"] = audio_ref
                    if entry.get("audio_content_type"):
                        record["audio_content_type"] = entry.get("audio_content_type")
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        for entry in selected:
            entry["exported_at"] = now_iso
            entry["updated_at"] = now_iso
        store["entries"] = entries
        self._save_correction_store(store)

        return {
            "success": True,
            "exported_total": len(selected),
            "filename": filename,
            "path": str(out_path),
            "message": "Exported text-only correction training pack. No audio paths were included.",
        }

    def _create_pending_correction_from_parse(
        self,
        *,
        parse_payload: dict[str, Any] | None,
        raw_transcript: str | None,
        retain_audio: bool = False,
        file_bytes: bytes | None = None,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> dict[str, Any] | None:
        payload = parse_payload or {}
        draft = (payload.get("draft_name") or "").strip()
        normalized = (payload.get("normalized_name") or "").strip()
        unit = (payload.get("unit") or "").strip()
        if payload.get("parse_status") != "parsed":
            return None
        if not draft or not normalized or draft == normalized:
            return None

        candidate = self.create_lexicon_candidate(
            alias=draft,
            canonical_name=normalized,
            unit=unit,
            raw_transcript=raw_transcript,
            source="qwen3-asr-lab-auto",
        )

        if retain_audio and file_bytes:
            audio_ref = self._persist_retained_audio(
                entry_id=candidate["entry"]["id"],
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )
            if audio_ref:
                store = self._load_correction_store()
                for entry in store.get("entries") or []:
                    if entry.get("id") == candidate["entry"]["id"]:
                        entry["audio_ref"] = audio_ref
                        entry["audio_content_type"] = content_type or ""
                        entry["updated_at"] = self._now_iso()
                        candidate["entry"]["audio_ref"] = audio_ref
                        candidate["entry"]["audio_content_type"] = content_type or ""
                        break
                self._save_correction_store(store)
        return candidate

    def _persist_retained_audio(
        self,
        *,
        entry_id: str,
        file_bytes: bytes,
        filename: str | None,
        content_type: str | None,
    ) -> str:
        audio_dir = Path(self.training_export_dir) / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename or "").suffix or self._guess_audio_suffix(content_type)
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", entry_id)
        out_name = f"{safe_id}{suffix}"
        out_path = audio_dir / out_name
        out_path.write_bytes(file_bytes)
        return f"audio/{out_name}"

    @staticmethod
    def _guess_audio_suffix(content_type: str | None) -> str:
        ct = (content_type or "").lower().strip()
        if "webm" in ct:
            return ".webm"
        if "wav" in ct:
            return ".wav"
        if "mp3" in ct or "mpeg" in ct:
            return ".mp3"
        if "ogg" in ct:
            return ".ogg"
        return ".bin"

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------
    def _model_cache_key(self, config: FunASRLabConfig) -> tuple[str, str]:
        return (
            (config.model or _DEFAULT_MODEL).strip() or _DEFAULT_MODEL,
            (config.device or _DEFAULT_DEVICE).strip() or _DEFAULT_DEVICE,
        )

    def _parse_qwen_output(
        self,
        output_text: str,
        *,
        forced_language: str | None = None,
    ) -> tuple[str, str]:
        text = output_text or ""
        language = ""
        transcript = text
        marker_index = text.find(QWEN_ASR_MODEL_TAG)
        if marker_index >= 0:
            prefix = text[:marker_index]
            transcript = text[marker_index + len(QWEN_ASR_MODEL_TAG):]
            if prefix.strip().lower().startswith("language "):
                language = prefix.strip()[len("language "):].strip()
        if forced_language:
            language = forced_language.strip().capitalize() or language
        return language, transcript.lstrip()

    def transcribe_audio(
        self,
        *,
        config: FunASRLabConfig,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> dict[str, Any]:
        if not self.is_dependency_available():
            raise FunASRLabError(self._qwen_provider.readiness_message())

        context_prompt = self._build_context_prompt(config)
        started = time.perf_counter()
        try:
            result: AsrTranscriptionResult = self._qwen_provider.transcribe_audio_with_options(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
                model=config.model,
                device=config.device,
                language=config.language,
                max_new_tokens=config.max_new_tokens,
                extra_context=config.extra_context,
                # Lab builds its own fully-formed context prompt and overrides
                # the provider-level domain context.
                use_domain_context=False,
                context_prompt_override=context_prompt,
            )
        except AsrProviderUnavailableError as exc:
            raise FunASRLabError(str(exc)) from exc
        duration_ms = result.duration_ms or int((time.perf_counter() - started) * 1000)

        asr_payload: dict[str, Any] = {
            "provider": result.provider,
            "model": result.model,
            "transcript": result.transcript,
            "quality_status": result.quality_status,
            "duration_ms": duration_ms,
            "warnings": list(result.warnings),
            "language": (result.raw_metadata or {}).get("language")
                or config.language
                or _DEFAULT_LANGUAGE,
            "raw_metadata": result.raw_metadata or {},
        }

        payload: dict[str, Any] = {
            "success": True,
            "asr": asr_payload,
            "baseline": None,
            "daily_intake_parse": None,
            "config": {
                "model": config.model,
                "device": config.device,
                "language": config.language,
                "max_new_tokens": config.max_new_tokens,
                "use_domain_context": config.use_domain_context,
                "extra_context": config.extra_context,
                "compare_with_baseline": config.compare_with_baseline,
                "parse_daily_intake": config.parse_daily_intake,
                "retain_training_audio": config.retain_training_audio,
                "intake_date": config.intake_date,
                "category": config.category,
            },
            "context_prompt": context_prompt,
            "lexicon_version": int(self._load_correction_store().get("lexicon_version") or 0),
        }
        return payload

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _today_str() -> str:
        return datetime.now().strftime("%Y-%m-%d")
