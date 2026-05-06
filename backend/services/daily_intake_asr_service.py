from __future__ import annotations

import os
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from backend.services.asr_provider import (
    AsrProviderError,
    AsrProviderName,
    AsrProviderTimeoutError,
    AsrTranscriptionResult,
)
from backend.services.asr_shadow_compare import AsrShadowCompareRecord, AsrShadowCompareStore
from backend.services.daily_intake_service import DailyIntakeService
from backend.services.qwen3_asr_provider import Qwen3AsrProvider
from backend.services.speech_to_text_service import SpeechToTextService


class DailyIntakeAsrError(RuntimeError):
    pass


@dataclass(slots=True)
class AsrProviderAttempt:
    provider: str
    result: AsrTranscriptionResult | None = None
    parse_payload: dict[str, Any] | None = None
    error: str = ""
    duration_ms: int = 0
    fallback_reason: str = ""

    @property
    def succeeded(self) -> bool:
        return self.result is not None and not self.error

    @property
    def parse_status(self) -> str:
        return str((self.parse_payload or {}).get("parse_status") or "")

    @property
    def quality_status(self) -> str:
        if self.result is None:
            return "error" if self.error else ""
        return self.result.quality_status


class DailyIntakeAsrService:
    provider_order = ("qwen3-asr", "faster-whisper")

    def __init__(
        self,
        *,
        qwen_provider=None,
        whisper_provider=None,
        daily_intake_service: DailyIntakeService | None = None,
        shadow_store: AsrShadowCompareStore | None = None,
    ) -> None:
        self.providers = {
            "qwen3-asr": qwen_provider or Qwen3AsrProvider(),
            "faster-whisper": whisper_provider or SpeechToTextService(),
        }
        self.daily_intake_service = daily_intake_service or DailyIntakeService()
        self.shadow_store = shadow_store or AsrShadowCompareStore()
        self.primary_provider = self._normalize_provider_name(
            os.getenv("DAILY_INTAKE_ASR_PRIMARY", "qwen3-asr"),
            default="qwen3-asr",
        )
        self.backup_provider = self._normalize_provider_name(
            os.getenv("DAILY_INTAKE_ASR_BACKUP", "faster-whisper"),
            default="faster-whisper",
        )
        if self.backup_provider == self.primary_provider:
            self.backup_provider = "faster-whisper" if self.primary_provider == "qwen3-asr" else "qwen3-asr"
        self.failover_enabled = self._env_bool("DAILY_INTAKE_ASR_FAILOVER", True)
        self.shadow_compare_enabled = self._env_bool("DAILY_INTAKE_ASR_SHADOW_COMPARE", True)

    def provider_name(self) -> str:
        return "daily-intake-asr"

    def is_configured(self) -> bool:
        return any(provider.is_configured() for provider in self.providers.values())

    def readiness_message(self) -> str:
        primary = self.providers[self.primary_provider]
        backup = self.providers[self.backup_provider]
        return (
            f"语音识别主模型：{self.primary_provider}（{primary.readiness_message()}）；"
            f"备用模型：{self.backup_provider}（{backup.readiness_message()}）。"
        )

    def capabilities(self) -> dict[str, Any]:
        providers = [self._diagnostics_payload(name, probe_runtime=False) for name in self.provider_order]
        primary_payload = next((item for item in providers if item["provider"] == self.primary_provider), None)
        enabled = any(bool(item.get("configured")) for item in providers)
        return {
            "success": True,
            "stable_transcription_enabled": enabled,
            "provider": self.primary_provider if enabled else None,
            "model": primary_payload.get("model") if primary_payload and enabled else None,
            "requested_device": primary_payload.get("requested_device") if primary_payload else None,
            "requested_compute_type": primary_payload.get("requested_compute_type") if primary_payload else None,
            "device": primary_payload.get("device") if primary_payload else None,
            "compute_type": primary_payload.get("compute_type") if primary_payload else None,
            "fallback_used": False,
            "fallback_reason": None,
            "primary_provider": self.primary_provider,
            "backup_provider": self.backup_provider,
            "failover_enabled": self.failover_enabled,
            "shadow_compare_enabled": self.shadow_compare_enabled,
            "providers": providers,
            "message": self.readiness_message(),
        }

    def diagnostics(self, *, probe_runtime: bool = False) -> dict[str, Any]:
        providers = [self._diagnostics_payload(name, probe_runtime=probe_runtime) for name in self.provider_order]
        primary_payload = next((item for item in providers if item["provider"] == self.primary_provider), providers[0])
        return {
            "success": True,
            "dependency_available": any(bool(item.get("dependency_available")) for item in providers),
            "provider": self.primary_provider,
            "model": primary_payload.get("model"),
            "requested_device": primary_payload.get("requested_device"),
            "requested_compute_type": primary_payload.get("requested_compute_type"),
            "resolved_device": primary_payload.get("device"),
            "resolved_compute_type": primary_payload.get("compute_type"),
            "effective_device": primary_payload.get("effective_device") or primary_payload.get("device"),
            "effective_compute_type": primary_payload.get("effective_compute_type") or primary_payload.get("compute_type"),
            "cuda_device_count": int(primary_payload.get("cuda_device_count") or 0),
            "supported_compute_types_cpu": primary_payload.get("supported_compute_types_cpu") or [],
            "supported_compute_types_cuda": primary_payload.get("supported_compute_types_cuda") or [],
            "missing_cuda_runtime_dlls": primary_payload.get("missing_cuda_runtime_dlls") or [],
            "model_loaded": any(bool(item.get("model_loaded")) for item in providers),
            "runtime_checked": probe_runtime,
            "fallback_used": False,
            "fallback_reason": None,
            "suggested_fix": primary_payload.get("suggested_fix"),
            "providers": providers,
            "primary_provider": self.primary_provider,
            "backup_provider": self.backup_provider,
            "failover_enabled": self.failover_enabled,
            "shadow_compare_enabled": self.shadow_compare_enabled,
            "message": self.readiness_message(),
        }

    def transcribe_audio(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        intake_date: str,
        category: str | None = None,
        asr_provider: str | None = "auto",
        fallback_enabled: bool | None = None,
    ) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        selected_provider = self._normalize_selection(asr_provider)
        provider_order = self._build_provider_order(selected_provider, fallback_enabled)
        attempts: dict[str, AsrProviderAttempt] = {}
        final_attempt: AsrProviderAttempt | None = None

        for index, provider_name in enumerate(provider_order):
            attempt = self._attempt_provider(
                provider_name=provider_name,
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
                intake_date=intake_date,
                category=category,
            )
            attempts[provider_name] = attempt
            if self._accept_attempt(attempt):
                final_attempt = attempt
                break
            if index == 0 and len(provider_order) > 1:
                attempt.fallback_reason = self._build_fallback_reason(attempt)

        if final_attempt is None:
            final_attempt = self._select_best_invalid_attempt(attempts)

        if final_attempt is None:
            self._record_shadow_safely(
                request_id=request_id,
                selected_provider=selected_provider,
                attempts=attempts,
                final_attempt=None,
            )
            errors = "; ".join(
                f"{name}: {attempt.error or attempt.fallback_reason or '未返回有效结果'}"
                for name, attempt in attempts.items()
            )
            raise DailyIntakeAsrError(f"所有语音识别模型都失败：{errors}")

        self._run_shadow_compare_safely(
            selected_provider=selected_provider,
            attempts=attempts,
            final_attempt=final_attempt,
            request_id=request_id,
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            intake_date=intake_date,
            category=category,
        )

        payload = dict(final_attempt.parse_payload or {})
        result = final_attempt.result
        fallback_used = final_attempt.provider != provider_order[0]
        fallback_reason = ""
        if fallback_used:
            first_attempt = attempts.get(provider_order[0])
            fallback_reason = self._build_fallback_reason(first_attempt) if first_attempt else "已切换到备用模型"
        payload["asr_provider"] = final_attempt.provider
        payload["asr_model"] = result.model if result else None
        payload["asr_fallback_used"] = fallback_used
        payload["asr_fallback_reason"] = fallback_reason
        payload["asr_duration_ms"] = result.duration_ms if result else final_attempt.duration_ms
        payload["asr_warnings"] = self._merge_warnings(final_attempt, fallback_reason)
        payload["asr_shadow_recorded"] = self.shadow_compare_enabled
        return payload

    def _attempt_provider(
        self,
        *,
        provider_name: str,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        intake_date: str,
        category: str | None,
    ) -> AsrProviderAttempt:
        started_at = time.perf_counter()
        try:
            provider = self.providers[provider_name]
            result = provider.transcribe_audio_for_provider(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )
            parse_payload = self.daily_intake_service.parse_transcript(
                transcript=result.transcript,
                intake_date=intake_date,
                category=category,
            )
            return AsrProviderAttempt(
                provider=provider_name,
                result=result,
                parse_payload=parse_payload,
                duration_ms=result.duration_ms or int((time.perf_counter() - started_at) * 1000),
            )
        except AsrProviderTimeoutError as exc:
            return AsrProviderAttempt(
                provider=provider_name,
                error=str(exc),
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                fallback_reason="模型推理超时",
            )
        except Exception as exc:
            return AsrProviderAttempt(
                provider=provider_name,
                error=str(exc),
                duration_ms=int((time.perf_counter() - started_at) * 1000),
                fallback_reason="模型转写失败",
            )

    def _accept_attempt(self, attempt: AsrProviderAttempt) -> bool:
        if not attempt.succeeded or not attempt.result or not attempt.parse_payload:
            return False
        if attempt.result.quality_status != "ok":
            return False
        return attempt.parse_payload.get("parse_status") == "parsed"

    def _select_best_invalid_attempt(self, attempts: dict[str, AsrProviderAttempt]) -> AsrProviderAttempt | None:
        for provider_name in (self.primary_provider, self.backup_provider):
            attempt = attempts.get(provider_name)
            if attempt and attempt.succeeded and attempt.parse_payload:
                return attempt
        for attempt in attempts.values():
            if attempt.succeeded and attempt.parse_payload:
                return attempt
        return None

    def _build_provider_order(self, selected_provider: str, fallback_enabled: bool | None) -> list[str]:
        if selected_provider == "auto":
            use_fallback = self.failover_enabled if fallback_enabled is None else fallback_enabled
            order = [self.primary_provider]
            if use_fallback and self.backup_provider != self.primary_provider:
                order.append(self.backup_provider)
            return order

        use_fallback = False if fallback_enabled is None else fallback_enabled
        order = [selected_provider]
        if use_fallback:
            backup = self.backup_provider if selected_provider != self.backup_provider else self.primary_provider
            if backup != selected_provider:
                order.append(backup)
        return order

    def _run_shadow_compare_safely(
        self,
        *,
        selected_provider: str,
        attempts: dict[str, AsrProviderAttempt],
        final_attempt: AsrProviderAttempt,
        request_id: str,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        intake_date: str,
        category: str | None,
    ) -> None:
        if not self.shadow_compare_enabled:
            return

        for provider_name in self.provider_order:
            if provider_name in attempts:
                continue
            attempts[provider_name] = self._attempt_provider(
                provider_name=provider_name,
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
                intake_date=intake_date,
                category=category,
            )
            break

        self._record_shadow_safely(
            request_id=request_id,
            selected_provider=selected_provider,
            attempts=attempts,
            final_attempt=final_attempt,
        )

    def _record_shadow_safely(
        self,
        *,
        request_id: str,
        selected_provider: str,
        attempts: dict[str, AsrProviderAttempt],
        final_attempt: AsrProviderAttempt | None,
    ) -> None:
        if not self.shadow_compare_enabled:
            return
        try:
            primary_attempt = attempts.get(self.primary_provider) or AsrProviderAttempt(provider=self.primary_provider)
            backup_attempt = attempts.get(self.backup_provider) or AsrProviderAttempt(provider=self.backup_provider)
            initial_provider = self.primary_provider if selected_provider == "auto" else selected_provider
            fallback_used = bool(final_attempt and final_attempt.provider != initial_provider)
            initial_attempt = attempts.get(initial_provider)
            self.shadow_store.append(
                AsrShadowCompareRecord(
                    request_id=request_id,
                    selected_provider=selected_provider,
                    primary_provider=self.primary_provider,
                    backup_provider=self.backup_provider,
                    final_provider=final_attempt.provider if final_attempt else "",
                    fallback_used=fallback_used,
                    fallback_reason=self._build_fallback_reason(initial_attempt) if fallback_used else "",
                    final_parse_status=final_attempt.parse_status if final_attempt else "",
                    primary_duration_ms=primary_attempt.duration_ms,
                    backup_duration_ms=backup_attempt.duration_ms,
                    primary_quality_status=primary_attempt.quality_status,
                    backup_quality_status=backup_attempt.quality_status,
                    primary_warnings=primary_attempt.result.warnings if primary_attempt.result else [],
                    backup_warnings=backup_attempt.result.warnings if backup_attempt.result else [],
                    primary_error=primary_attempt.error,
                    backup_error=backup_attempt.error,
                    primary_transcript=primary_attempt.result.transcript if primary_attempt.result else "",
                    backup_transcript=backup_attempt.result.transcript if backup_attempt.result else "",
                )
            )
        except Exception:
            return

    def _diagnostics_payload(self, provider_name: str, *, probe_runtime: bool) -> dict[str, Any]:
        provider = self.providers[provider_name]
        try:
            diagnostics = provider.diagnostics(probe_runtime=probe_runtime)
            payload = asdict(diagnostics)
        except Exception as exc:
            payload = {
                "provider": provider_name,
                "model": getattr(provider, "model", ""),
                "dependency_available": False,
                "configured": False,
                "model_loaded": False,
                "message": str(exc),
            }
        raw = payload.pop("raw", {}) or {}
        payload.update(raw)
        return payload

    def _build_fallback_reason(self, attempt: AsrProviderAttempt | None) -> str:
        if attempt is None:
            return "主模型未返回结果"
        if attempt.error:
            return attempt.error
        if attempt.result and attempt.result.quality_status != "ok":
            return "主模型质量不达标"
        if attempt.parse_payload and attempt.parse_payload.get("parse_status") != "parsed":
            return str(attempt.parse_payload.get("message") or "主模型结果无法解析为点货条目")
        return attempt.fallback_reason or "已切换到备用模型"

    def _merge_warnings(self, attempt: AsrProviderAttempt, fallback_reason: str) -> list[str]:
        warnings: list[str] = []
        if attempt.parse_payload:
            warnings.extend(str(item) for item in attempt.parse_payload.get("warnings") or [])
        if attempt.result:
            warnings.extend(attempt.result.warnings)
        if fallback_reason:
            warnings.append(f"已回退到备用模型：{fallback_reason}")
        return list(dict.fromkeys(warnings))

    def _normalize_selection(self, value: str | None) -> str:
        normalized = str(value or "auto").strip().lower() or "auto"
        if normalized in {"auto", "qwen3-asr", "faster-whisper"}:
            return normalized
        raise ValueError("asr_provider 只支持 auto、qwen3-asr 或 faster-whisper。")

    def _normalize_provider_name(self, value: str | None, *, default: AsrProviderName) -> AsrProviderName:
        normalized = str(value or default).strip().lower() or default
        if normalized not in {"qwen3-asr", "faster-whisper"}:
            return default
        return normalized  # type: ignore[return-value]

    def _env_bool(self, name: str, default: bool) -> bool:
        raw_value = os.getenv(name)
        if raw_value is None:
            return default
        return raw_value.strip().lower() not in {"0", "false", "no"}
