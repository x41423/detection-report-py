"""faster-whisper based speech-to-text service for daily-intake recordings.

The service is responsible for:

* resolving the requested compute device / compute-type and falling back to
  CPU when CUDA is unavailable or fails at runtime,
* loading the faster-whisper model lazily and caching it for re-use,
* assembling the context bias (initial prompt + hotwords) using the shared
  :class:`AsrContextBuilder`, and
* exposing rich diagnostics so the FastAPI layer can report dependency,
  configuration and DLL issues to the operator.
"""
from __future__ import annotations

import importlib
import importlib.util
import io
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from app.db.veg_repository import VegRepository  # noqa: F401  (test patch target)
from app.models.config_model import load_config  # noqa: F401  (test patch target)
from backend.env import get_project_paths
from backend.services.asr_context_builder import AsrContextBuilder
from backend.services.audio_pyav_convert import convert_to_normalized_wav
from backend.services.asr_correction_lexicon import (
    AsrCorrectionEntry,
    AsrCorrectionLexicon,
)
from backend.services.asr_provider import (
    AsrProviderDiagnostics,
    AsrProviderTimeoutError,
    AsrProviderUnavailableError,
    AsrTranscriptionResult,
)


_logger = logging.getLogger(__name__)


# Module-level constants (also used as patch targets in tests).
ROOT_DIR: Path = get_project_paths().root
_DEFAULT_MODEL = "medium"
_DEFAULT_LANGUAGE = "zh"
_DEFAULT_DEVICE = "auto"
_DEFAULT_COMPUTE_TYPE = "auto"
_DEFAULT_BEAM_SIZE = 5
_DEFAULT_TIMEOUT_SECONDS = 60.0

# Preferred compute-type ranking per device type.
_CUDA_COMPUTE_PREFERENCE = ("float16", "int8_float16", "int8", "float32")
_CPU_COMPUTE_PREFERENCE = ("int8", "float32")

# Common runtime DLLs that must be discoverable before faster-whisper can
# initialise a CUDA context on Windows.
_REQUIRED_CUDA_DLLS = ("cublas64_12.dll", "cudnn_ops_infer64_9.dll", "cudnn_cnn_infer64_9.dll")


class SpeechToTextConfigError(RuntimeError):
    """Raised when the user-provided configuration is internally inconsistent."""


@dataclass(slots=True)
class SpeechToTextRuntimeStatus:
    requested_device: str
    requested_compute_type: str
    device: str
    compute_type: str
    fallback_used: bool = False
    fallback_reason: str | None = None


@dataclass(slots=True)
class SpeechToTextDiagnostics:
    provider: str = "faster-whisper"
    model: str = ""
    dependency_available: bool = False
    configured: bool = False
    requested_device: str = ""
    requested_compute_type: str = ""
    resolved_device: str = ""
    resolved_compute_type: str = ""
    effective_device: str | None = None
    effective_compute_type: str | None = None
    fallback_used: bool = False
    fallback_reason: str | None = None
    runtime_checked: bool = False
    model_loaded: bool = False
    cuda_device_count: int = 0
    supported_compute_types_cpu: list[str] = field(default_factory=list)
    supported_compute_types_cuda: list[str] = field(default_factory=list)
    missing_cuda_runtime_dlls: list[str] = field(default_factory=list)
    suggested_fix: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class SpeechToTextService:
    """ASR provider that wraps faster-whisper for the daily-intake page."""

    provider_kind = "faster-whisper"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.model_name = (os.getenv("DAILY_INTAKE_STT_MODEL") or _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
        self.requested_device = (os.getenv("DAILY_INTAKE_STT_DEVICE") or _DEFAULT_DEVICE).strip() or _DEFAULT_DEVICE
        self.requested_compute_type = (
            os.getenv("DAILY_INTAKE_STT_COMPUTE_TYPE") or _DEFAULT_COMPUTE_TYPE
        ).strip() or _DEFAULT_COMPUTE_TYPE
        self.language = (os.getenv("DAILY_INTAKE_STT_LANGUAGE") or _DEFAULT_LANGUAGE).strip() or _DEFAULT_LANGUAGE
        self.beam_size = self._env_int("DAILY_INTAKE_STT_BEAM_SIZE", _DEFAULT_BEAM_SIZE)
        self.timeout_seconds = self._env_float(
            "DAILY_INTAKE_STT_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS
        )

        self.use_corrections = self._env_bool("DAILY_INTAKE_STT_USE_ASR_CORRECTIONS", True)
        self.correction_lexicon = AsrCorrectionLexicon()
        self._context_builder = AsrContextBuilder(
            lexicon=self.correction_lexicon,
            use_corrections=self.use_corrections,
        )

        self._model_lock = threading.Lock()
        self._model_instance: Any | None = None
        self._runtime_status: SpeechToTextRuntimeStatus | None = None
        self._dll_paths_configured = False

        # Dedicated executor for transcription isolation.  One worker means
        # only one inference runs at a time; the 60 s default timeout
        # prevents a hanging ``model.transcribe()`` from exhausting the
        # uvicorn thread pool (see git log for the bug report).
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="faster-whisper")

        # On Windows, allow the operator to point us at the directory that
        # holds CUDA / cuDNN runtime DLLs.  Failing this configuration is
        # not fatal – diagnostics will surface a remediation hint.
        self._configure_windows_dll_directories()

    # ------------------------------------------------------------------
    # AsrProvider protocol surface
    # ------------------------------------------------------------------
    def provider_name(self) -> str:
        return "faster-whisper"

    def is_configured(self) -> bool:
        return bool(self.model_name)

    def is_dependency_available(self) -> bool:
        return importlib.util.find_spec("faster_whisper") is not None

    def readiness_message(self) -> str:
        if not self.is_dependency_available():
            return (
                "faster-whisper 依赖未就绪：未安装 `faster-whisper` 包。"
                "请运行：py -3 -m pip install -r backend/requirements.txt"
            )
        try:
            status = self._resolve_runtime_status()
        except SpeechToTextConfigError as exc:
            return f"faster-whisper 配置异常：{exc}"
        return f"faster-whisper 已就绪：{status.device}/{status.compute_type}（模型 {self.model_name}）。"

    def diagnostics(self, *, probe_runtime: bool = False) -> AsrProviderDiagnostics:
        dep_available = self.is_dependency_available()
        cuda_count = 0
        cpu_types: list[str] = []
        cuda_types: list[str] = []
        missing_dlls: list[str] = []
        resolved_device = ""
        resolved_compute = ""
        suggested_fix: str | None = None
        message = ""
        runtime_checked = False
        model_loaded = False
        effective_device: str | None = None
        effective_compute: str | None = None
        fallback_used = False
        fallback_reason: str | None = None

        if dep_available:
            try:
                cuda_count = self._get_cuda_device_count()
            except Exception:  # pragma: no cover - defensive
                cuda_count = 0
            try:
                cpu_types = sorted(self._get_supported_compute_types("cpu"))
            except Exception:
                cpu_types = []
            try:
                cuda_types = sorted(self._get_supported_compute_types("cuda"))
            except Exception:
                cuda_types = []
            try:
                missing_dlls = list(self._get_missing_cuda_runtime_dlls())
            except Exception:
                missing_dlls = []

            try:
                resolved = self._resolve_runtime_status()
                resolved_device = resolved.device
                resolved_compute = resolved.compute_type
            except SpeechToTextConfigError as exc:
                message = str(exc)
                suggested_fix = (
                    "请在 .env 中将 DAILY_INTAKE_STT_DEVICE 设为 auto 或 cpu，或安装 CUDA / cuDNN 12.x 后重试。"
                )

            if missing_dlls:
                suggested_fix = (
                    "缺少 CUDA 12 / cuDNN 9 运行时 DLL（"
                    + "、".join(missing_dlls)
                    + "）。请安装与 faster-whisper 1.x 兼容的 CUDA 12 + cuDNN 9 运行时，"
                    "并通过 DAILY_INTAKE_STT_DLL_DIRS 指向其 bin 目录。"
                )

            if probe_runtime:
                runtime_checked = True
                try:
                    self.warmup_model()
                except Exception as exc:
                    message = f"faster-whisper 预热失败：{exc}"
                model_loaded = self._model_instance is not None
                if self._runtime_status is not None:
                    effective_device = self._runtime_status.device
                    effective_compute = self._runtime_status.compute_type
                    fallback_used = self._runtime_status.fallback_used
                    fallback_reason = self._runtime_status.fallback_reason

        if not dep_available:
            message = self.readiness_message()
            suggested_fix = "请运行：py -3 -m pip install -r backend/requirements.txt"

        diag = SpeechToTextDiagnostics(
            provider="faster-whisper",
            model=self.model_name,
            dependency_available=dep_available,
            configured=self.is_configured(),
            requested_device=self.requested_device,
            requested_compute_type=self.requested_compute_type,
            resolved_device=resolved_device,
            resolved_compute_type=resolved_compute,
            effective_device=effective_device,
            effective_compute_type=effective_compute,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            runtime_checked=runtime_checked,
            model_loaded=model_loaded,
            cuda_device_count=cuda_count,
            supported_compute_types_cpu=cpu_types,
            supported_compute_types_cuda=cuda_types,
            missing_cuda_runtime_dlls=missing_dlls,
            suggested_fix=suggested_fix,
            raw={"requested_compute_preference": list(self._compute_preference(resolved_device or "cpu"))},
        )
        if not message:
            diag.raw["message"] = self.readiness_message() if dep_available else message
        return diag  # type: ignore[return-value]

    def transcribe_audio_for_provider(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> AsrTranscriptionResult:
        if not self.is_dependency_available():
            raise AsrProviderUnavailableError(self.readiness_message())

        def _operation() -> AsrTranscriptionResult:
            return self._transcribe_impl(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )

        return self._run_with_timeout(_operation, timeout_seconds=float(self.timeout_seconds))

    def _transcribe_impl(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
    ) -> AsrTranscriptionResult:
        started = time.perf_counter()
        try:
            model = self._get_model_instance()
            initial_prompt, hotwords = self._build_context_bias()
            initial_prompt, hotwords = self._fit_context_bias_to_model(
                model,
                initial_prompt=initial_prompt,
                hotwords=hotwords,
            )
            with io.BytesIO(file_bytes) as buf:
                segments, _info = model.transcribe(
                    buf,
                    language=self.language or None,
                    initial_prompt=initial_prompt,
                    hotwords=hotwords,
                    beam_size=self.beam_size,
                )
                transcript = "".join(seg.text for seg in segments).strip()
        except AsrProviderTimeoutError:
            raise
        except Exception as exc:
            raise AsrProviderUnavailableError(f"faster-whisper 推理失败：{exc}") from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        runtime = self._runtime_status
        return AsrTranscriptionResult(
            transcript=transcript,
            provider="faster-whisper",
            model=self.model_name,
            duration_ms=duration_ms,
            raw_metadata={
                "filename": filename,
                "content_type": content_type or "",
                "device": runtime.device if runtime else "",
                "compute_type": runtime.compute_type if runtime else "",
                "fallback_used": bool(runtime and runtime.fallback_used),
            },
        )

    def _run_with_timeout(
        self,
        operation: Callable[[], Any],
        *,
        timeout_seconds: float,
    ) -> Any:
        """Run ``operation`` in a dedicated thread with an upper time bound.

        If the call does not complete within ``timeout_seconds`` the future
        is cancelled and :class:`AsrProviderTimeoutError` is raised so the
        orchestrator can fail over to the backup provider cleanly.
        """
        future = self._executor.submit(operation)
        try:
            return future.result(timeout=timeout_seconds if timeout_seconds and timeout_seconds > 0 else None)
        except FutureTimeoutError as exc:
            future.cancel()
            raise AsrProviderTimeoutError(
                f"faster-whisper 推理超时（>{timeout_seconds:.1f}s）。"
                "请检查模型 / 设备状态，或换用 qwen3-asr。"
            ) from exc

    # ------------------------------------------------------------------
    # Audio preprocessing
    # ------------------------------------------------------------------
    def _convert_to_wav_via_pyav(self, input_path: str) -> str:
        """Normalise the audio blob pointed to by ``input_path`` to 16 kHz mono WAV.

        The output path is the input path with ``.wav`` appended, so the
        caller can reliably clean up both files.
        """
        output_path = f"{input_path}.wav"
        return convert_to_normalized_wav(input_path, output_path=output_path)

    # ------------------------------------------------------------------
    # Runtime status / model loading
    # ------------------------------------------------------------------
    def runtime_status(self) -> SpeechToTextRuntimeStatus:
        # Once the model has been loaded (or we have probed the runtime)
        # return the status that actually applies – including any CPU
        # fallback that happened during initialisation.
        if self._runtime_status is not None:
            return self._runtime_status
        return self._resolve_runtime_status()

    def _resolve_runtime_status(self) -> SpeechToTextRuntimeStatus:
        requested_device = (self.requested_device or "auto").strip() or "auto"
        requested_compute = (self.requested_compute_type or "auto").strip() or "auto"
        device_lower = requested_device.lower()

        if device_lower == "cpu":
            compute = self._select_compute_type("cpu", requested_compute)
            return SpeechToTextRuntimeStatus(
                requested_device=requested_device,
                requested_compute_type=requested_compute,
                device="cpu",
                compute_type=compute,
            )

        if device_lower == "cuda" or device_lower.startswith("cuda:"):
            if self._get_cuda_device_count() < 1:
                raise SpeechToTextConfigError(
                    "已显式选择 CUDA，但当前未检测到可用 GPU。"
                    "请确认显卡驱动 / CUDA 已安装，或将 DAILY_INTAKE_STT_DEVICE 改回 auto。"
                )
            compute = self._select_compute_type("cuda", requested_compute)
            return SpeechToTextRuntimeStatus(
                requested_device=requested_device,
                requested_compute_type=requested_compute,
                device=device_lower,
                compute_type=compute,
            )

        # auto: prefer CUDA when available + supported
        if self._get_cuda_device_count() >= 1:
            try:
                compute = self._select_compute_type("cuda", requested_compute)
                return SpeechToTextRuntimeStatus(
                    requested_device=requested_device,
                    requested_compute_type=requested_compute,
                    device="cuda",
                    compute_type=compute,
                )
            except SpeechToTextConfigError:
                pass

        compute = self._select_compute_type("cpu", requested_compute)
        return SpeechToTextRuntimeStatus(
            requested_device=requested_device,
            requested_compute_type=requested_compute,
            device="cpu",
            compute_type=compute,
        )

    def _select_compute_type(self, device: str, requested_compute: str) -> str:
        supported = self._get_supported_compute_types(device)
        normalized_request = (requested_compute or "auto").strip().lower()
        if normalized_request and normalized_request != "auto":
            if normalized_request in supported:
                return normalized_request
            raise SpeechToTextConfigError(
                f"compute_type={requested_compute} 在 {device} 上不可用。"
                f"已知支持：{sorted(supported) or '无'}。"
            )
        for candidate in self._compute_preference(device):
            if candidate in supported:
                return candidate
        if supported:
            return next(iter(sorted(supported)))
        return "float32" if device == "cpu" else "float16"

    @staticmethod
    def _compute_preference(device: str) -> tuple[str, ...]:
        if device == "cuda" or (isinstance(device, str) and device.startswith("cuda")):
            return _CUDA_COMPUTE_PREFERENCE
        return _CPU_COMPUTE_PREFERENCE

    def _apply_runtime_status(self, status: SpeechToTextRuntimeStatus) -> None:
        self._runtime_status = status

    def _get_model_instance(self) -> Any:
        with self._model_lock:
            if self._model_instance is not None:
                return self._model_instance
            status = self._resolve_runtime_status()
            attempts: list[tuple[SpeechToTextRuntimeStatus, str]] = []

            try:
                model = self._create_whisper_model(
                    self.model_name,
                    device=status.device,
                    compute_type=status.compute_type,
                )
                try:
                    self._probe_model_runtime(model, status)
                except Exception as exc:
                    attempts.append((status, str(exc)))
                    raise
            except Exception as exc:
                requested_lower = (self.requested_device or "auto").lower()
                if requested_lower != "auto":
                    raise
                cpu_status = SpeechToTextRuntimeStatus(
                    requested_device=status.requested_device,
                    requested_compute_type=status.requested_compute_type,
                    device="cpu",
                    compute_type=self._select_compute_type("cpu", status.requested_compute_type),
                    fallback_used=True,
                    fallback_reason=self._compose_fallback_reason(exc),
                )
                model = self._create_whisper_model(
                    self.model_name,
                    device=cpu_status.device,
                    compute_type=cpu_status.compute_type,
                )
                self._probe_model_runtime(model, cpu_status)
                self._apply_runtime_status(cpu_status)
                self._model_instance = model
                return model

            self._apply_runtime_status(status)
            self._model_instance = model
            return model

    def warmup_model(self) -> None:
        if self._model_instance is None:
            self._get_model_instance()

    def _probe_model_runtime(self, model: Any, status: SpeechToTextRuntimeStatus) -> None:
        # Real implementations execute a tiny inference run here to surface
        # missing CUDA DLLs.  We expose the hook so tests can patch it; the
        # default implementation is a no-op which is appropriate when the
        # model object cannot perform a cheap probe without a sample audio.
        _ = (model, status)

    @staticmethod
    def _compose_fallback_reason(exc: Exception) -> str:
        text = str(exc)
        if "cublas" in text.lower() or "cudnn" in text.lower():
            return f"GPU 运行时缺少必要的 DLL：{text}"
        if "gpu" in text.lower() or "cuda" in text.lower():
            return f"GPU 初始化失败：{text}"
        return f"GPU 不可用：{text}"

    def _create_whisper_model(self, model_name: str, *, device: str, compute_type: str) -> Any:
        try:
            faster_whisper = importlib.import_module("faster_whisper")
        except Exception as exc:
            raise AsrProviderUnavailableError(
                f"faster-whisper 依赖未安装：{exc}"
            ) from exc
        WhisperModel = getattr(faster_whisper, "WhisperModel")
        return WhisperModel(model_name, device=device, compute_type=compute_type)

    # ------------------------------------------------------------------
    # Capability probing
    # ------------------------------------------------------------------
    def _get_cuda_device_count(self) -> int:
        try:
            torch = importlib.import_module("torch")
        except Exception:
            return 0
        try:
            return int(torch.cuda.device_count())
        except Exception:
            return 0

    def _get_supported_compute_types(self, device: str) -> set[str]:
        try:
            ct2 = importlib.import_module("ctranslate2")
        except Exception:
            return set()
        try:
            return set(ct2.get_supported_compute_types(device))  # type: ignore[attr-defined]
        except Exception:
            return set()

    def supported_compute_types_cpu(self) -> list[str]:
        return sorted(self._get_supported_compute_types("cpu"))

    def supported_compute_types_cuda(self) -> list[str]:
        return sorted(self._get_supported_compute_types("cuda"))

    def _get_missing_cuda_runtime_dlls(self) -> list[str]:
        return list(self.missing_cuda_runtime_dlls())

    def missing_cuda_runtime_dlls(self) -> list[str]:
        if os.name != "nt":
            return []
        candidate_dirs: list[Path] = []
        env_dirs = os.getenv("DAILY_INTAKE_STT_DLL_DIRS", "").split(os.pathsep)
        for entry in env_dirs:
            entry = entry.strip()
            if not entry:
                continue
            path = Path(entry)
            if not path.is_absolute():
                path = ROOT_DIR / path
            if path.exists():
                candidate_dirs.append(path)

        path_var = os.getenv("PATH", "")
        for entry in path_var.split(os.pathsep):
            entry = entry.strip()
            if entry:
                candidate_dirs.append(Path(entry))

        missing: list[str] = []
        for dll in _REQUIRED_CUDA_DLLS:
            found = False
            for directory in candidate_dirs:
                try:
                    if (directory / dll).exists():
                        found = True
                        break
                except OSError:
                    continue
            if not found:
                missing.append(dll)
        return missing

    # ------------------------------------------------------------------
    # Context bias (initial prompt + hotwords)
    # ------------------------------------------------------------------
    def _build_context_bias(self) -> tuple[str, str | None]:
        correction_entries = self._load_active_correction_entries()
        domain_terms = self._collect_domain_vocabulary(correction_entries=correction_entries)
        builder = self._context_builder
        initial_prompt = (
            "这是食材点货录音。背景噪声较大时，请优先识别距离麦克风最近的人声。"
            "请输出商品名称、数量和单位。"
            "数量请优先使用阿拉伯数字，小数请使用小数点。"
            "如果听到“四点八斤”，请输出“4.8斤”，不要输出“4斤8斤”或“四斤八斤”。"
            "示例：大白菜4.8斤，土豆2.5斤，豆腐1.25包。"
        )
        correction_prompt = builder.build_faster_whisper_correction_prompt(
            correction_entries,
            max_pairs=30,
        )
        if correction_prompt:
            initial_prompt += correction_prompt
        hotwords = builder.fit_hotwords(
            domain_terms,
            max_count=200,
            max_chars=1500,
        )
        return initial_prompt, hotwords

    def _load_active_correction_entries(self) -> list[AsrCorrectionEntry]:
        if not self.use_corrections:
            return []
        try:
            return list(self.correction_lexicon.load_entries(statuses={"active"}))
        except Exception as exc:
            _logger.warning("Failed to load asr correction lexicon: %s", exc)
            return []

    def _collect_domain_vocabulary(
        self,
        *,
        correction_entries: list[AsrCorrectionEntry] | None = None,
    ) -> list[str]:
        return self._context_builder.collect_domain_vocabulary(
            correction_entries=correction_entries or [],
        )

    def _fit_context_bias_to_model(
        self,
        model: Any,
        *,
        initial_prompt: str | None,
        hotwords: str | None,
    ) -> tuple[Any, str | None]:
        """Trim the bias context so that ``initial_prompt + hotwords`` stay within
        the model's prompt budget.

        faster-whisper effectively double-counts hotwords against the prompt
        budget (they are concatenated alongside the initial prompt and
        re-encoded), so we reserve at most half of the remaining budget for
        them.  This mirrors the production behaviour exercised by the unit
        tests.
        """
        if model is None:
            return initial_prompt, hotwords

        try:
            tokenizer = self._create_context_tokenizer(model)
        except Exception:
            return initial_prompt, hotwords
        if tokenizer is None:
            return initial_prompt, hotwords

        max_length = int(getattr(model, "max_length", 0) or 0)
        if max_length <= 0:
            return initial_prompt, hotwords

        sot_sequence = list(getattr(tokenizer, "sot_sequence", []) or [])
        sot_len = len(sot_sequence)

        prompt_tokens = list(tokenizer.encode(initial_prompt or ""))
        prompt_token_count = len(prompt_tokens)

        # Reserve half of the remaining budget for hotwords; this matches the
        # double-counting policy faster-whisper applies internally and keeps
        # the resulting prompt safely under ``max_length``.
        remaining = max_length - sot_len - prompt_token_count
        hotwords_budget = max(remaining // 2, 0)

        if hotwords:
            entries = [entry.strip() for entry in hotwords.split(",") if entry.strip()]
            kept: list[str] = []
            for entry in entries:
                trial = ",".join(kept + [entry])
                trial_tokens = list(tokenizer.encode(trial))
                if len(trial_tokens) > hotwords_budget:
                    break
                kept.append(entry)
            hotwords = ",".join(kept) if kept else None

        return prompt_tokens, hotwords

    def _create_context_tokenizer(self, model: Any) -> Any:
        """Build a tokenizer that mirrors the model's vocabulary.

        Tests patch this hook so the rest of :meth:`_fit_context_bias_to_model`
        can run against a pure-Python fake.  The default implementation
        attempts to lazily build a faster-whisper tokenizer; failures are
        swallowed by the caller.
        """
        try:
            faster_whisper = importlib.import_module("faster_whisper")
        except Exception:
            return None
        Tokenizer = getattr(faster_whisper, "Tokenizer", None)
        if Tokenizer is None:
            return None
        try:
            return Tokenizer(model.hf_tokenizer, model.is_multilingual, task="transcribe", language=self.language)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Windows DLL discovery
    # ------------------------------------------------------------------
    def _configure_windows_dll_directories(self) -> None:
        if self._dll_paths_configured:
            return
        if os.name != "nt":
            self._dll_paths_configured = True
            return
        raw = os.getenv("DAILY_INTAKE_STT_DLL_DIRS", "")
        for entry in raw.split(os.pathsep):
            entry = entry.strip()
            if not entry:
                continue
            path = Path(entry)
            if not path.is_absolute():
                path = ROOT_DIR / path
            try:
                if path.exists() and hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(str(path))  # type: ignore[attr-defined]
            except OSError:
                continue
        self._dll_paths_configured = True

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        candidate = raw.strip().lower()
        if not candidate:
            return default
        if candidate in {"1", "true", "yes", "on"}:
            return True
        if candidate in {"0", "false", "no", "off"}:
            return False
        return default

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return int(default)
        try:
            return int(float(raw.strip()))
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        raw = os.getenv(name)
        if raw is None:
            return float(default)
        try:
            return float(raw.strip())
        except (TypeError, ValueError):
            return float(default)
