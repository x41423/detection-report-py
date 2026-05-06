from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


AsrProviderName = Literal["qwen3-asr", "faster-whisper"]
AsrQualityStatus = Literal["ok", "low_quality", "invalid", "timeout", "error"]


@dataclass(slots=True)
class AsrTranscriptionResult:
    transcript: str
    provider: AsrProviderName
    model: str
    quality_status: AsrQualityStatus = "ok"
    confidence: float | None = None
    duration_ms: int = 0
    warnings: list[str] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AsrProviderDiagnostics:
    provider: AsrProviderName
    model: str
    dependency_available: bool
    configured: bool
    model_loaded: bool = False
    requested_device: str | None = None
    device: str | None = None
    timeout_seconds: float | None = None
    max_concurrency: int | None = None
    message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class AsrProviderError(RuntimeError):
    pass


class AsrProviderUnavailableError(AsrProviderError):
    pass


class AsrProviderTimeoutError(AsrProviderError):
    pass


class AsrProvider(Protocol):
    def provider_name(self) -> AsrProviderName:
        ...

    def is_configured(self) -> bool:
        ...

    def readiness_message(self) -> str:
        ...

    def diagnostics(self, *, probe_runtime: bool = False) -> AsrProviderDiagnostics:
        ...

    def transcribe_audio_for_provider(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> AsrTranscriptionResult:
        ...
