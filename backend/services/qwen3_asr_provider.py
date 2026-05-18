"""Qwen3-ASR provider for transcribing daily-intake audio clips.

The provider wraps the HuggingFace ``Qwen3-ASR`` model family.  Heavy
dependencies (``transformers``, ``accelerate`` and the optional ``qwen-asr``
package) are imported lazily so that unit tests and the FastAPI app can keep
running on machines without GPU support.
"""
from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import io
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable

from backend.services.audio_pyav_convert import (
    convert_to_normalized_wav,
    soundfile_can_read,
)
from backend.services.asr_provider import (
    AsrProviderDiagnostics,
    AsrProviderTimeoutError,
    AsrProviderUnavailableError,
    AsrTranscriptionResult,
)


_logger = logging.getLogger(__name__)

# The Qwen3-ASR model emits the recognised transcript right after a marker
# tag.  Tests pin both the constant and the parsing behaviour.
QWEN_ASR_MODEL_TAG = "<asr_text>"

# Default tuning knobs.  Each one can be overridden via the matching
# ``DAILY_INTAKE_QWEN3_ASR_*`` environment variable.
_DEFAULT_MODEL = "Qwen/Qwen3-ASR-1.7B"
_DEFAULT_DEVICE = "auto"
_DEFAULT_LANGUAGE = "Chinese"
_DEFAULT_TIMEOUT_SECONDS = 30.0
_DEFAULT_MAX_NEW_TOKENS = 256
_DEFAULT_MAX_CONCURRENCY = 1

_REQUIRED_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    # (distribution_name, importable_module)
    ("qwen-asr", "qwen_asr"),
    ("transformers", "transformers"),
    ("accelerate", "accelerate"),
)


_AUDIO_CONTENT_TYPE_SUFFIX: dict[str, str] = {
    "audio/webm": ".webm",
    "audio/webm;codecs=opus": ".webm",
    "audio/ogg": ".ogg",
    "audio/ogg;codecs=opus": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
}


def _guess_audio_suffix(filename: str, content_type: str | None) -> str:
    """Return a sensible file extension for a PyAV-decodable temp file."""
    if filename:
        _, ext = os.path.splitext(filename)
        if ext:
            return ext.lower()
    if content_type:
        key = content_type.strip().lower()
        if key in _AUDIO_CONTENT_TYPE_SUFFIX:
            return _AUDIO_CONTENT_TYPE_SUFFIX[key]
        bare = key.split(";", 1)[0].strip()
        if bare in _AUDIO_CONTENT_TYPE_SUFFIX:
            return _AUDIO_CONTENT_TYPE_SUFFIX[bare]
    return ".bin"


def _ensure_qwen_asr_importable() -> None:
    """Neutralise optional ``nagisa`` dependency so ``qwen_asr`` imports cleanly.

    ``qwen_asr`` pulls in ``nagisa`` only for Japanese forced alignment. On some
    Windows setups the shipped ``nagisa_v001.model`` binary cannot be loaded by
    ``dynet`` (``RuntimeError: Could not read model from ...``) and the failure
    surfaces as a ``RuntimeError`` at ``qwen_asr`` top-level import time. We do
    not need Japanese alignment for Chinese daily-intake ASR, so register a
    no-op stub before importing.
    """
    import sys
    import types

    if "nagisa" in sys.modules:
        return

    try:  # optimistic: try the real thing first
        import nagisa  # type: ignore[import-not-found]  # noqa: F401
        return
    except Exception as exc:  # pragma: no cover - environmental
        _logger.debug("Stubbing out broken nagisa import: %s", exc)

    stub = types.ModuleType("nagisa")
    stub.tagging = lambda *_args, **_kwargs: []  # type: ignore[attr-defined]
    stub.Tagger = type("Tagger", (), {})  # type: ignore[attr-defined]
    sys.modules["nagisa"] = stub


class Qwen3AsrProvider:
    """ASR provider backed by the Qwen3-ASR HuggingFace pipeline."""

    provider_kind = "qwen3-asr"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.model_name = os.getenv("DAILY_INTAKE_QWEN3_ASR_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
        self.requested_device = os.getenv("DAILY_INTAKE_QWEN3_ASR_DEVICE", _DEFAULT_DEVICE).strip() or _DEFAULT_DEVICE
        self.default_language = os.getenv("DAILY_INTAKE_QWEN3_ASR_LANGUAGE", _DEFAULT_LANGUAGE).strip() or _DEFAULT_LANGUAGE
        self.timeout_seconds = self._env_float(
            "DAILY_INTAKE_QWEN3_ASR_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT_SECONDS
        )
        self.max_new_tokens = self._env_int(
            "DAILY_INTAKE_QWEN3_ASR_MAX_NEW_TOKENS", _DEFAULT_MAX_NEW_TOKENS
        )
        self.max_concurrency = max(
            self._env_int("DAILY_INTAKE_QWEN3_ASR_MAX_CONCURRENCY", _DEFAULT_MAX_CONCURRENCY),
            1,
        )
        # API key for cloud fallback (DashScope/Qwen-ASR REST).  Optional.
        self.api_key = (os.getenv("DAILY_INTAKE_QWEN3_ASR_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or "").strip()

        self._model_lock = threading.Lock()
        self._model_bundle: tuple[Any, Any] | None = None  # (model, processor)
        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrency, thread_name_prefix="qwen3-asr")

    # ------------------------------------------------------------------
    # AsrProvider protocol surface
    # ------------------------------------------------------------------
    def provider_name(self) -> str:
        return "qwen3-asr"

    def is_configured(self) -> bool:
        return bool(self.model_name) and self.is_dependency_available()

    def is_dependency_available(self) -> bool:
        return not self._collect_missing_dependencies()

    def readiness_message(self) -> str:
        missing = self._collect_missing_dependencies()
        if not missing:
            return f"Qwen3-ASR 已就绪：模型 {self.model_name}（设备 {self.requested_device}）。"
        joined = "、".join(missing)
        return (
            f"Qwen3-ASR 依赖未就绪，缺少：{joined}。"
            "请在 backend/requirements.txt 中安装；如本机暂时缺 GPU，可改用 faster-whisper 备用通道。"
        )

    def diagnostics(self, *, probe_runtime: bool = False) -> AsrProviderDiagnostics:
        missing = self._collect_missing_dependencies()
        dependency_available = not missing
        configured = self.is_configured()
        device = None
        cuda_device_count = 0
        if dependency_available:
            try:
                device = self._resolve_device()
            except Exception:  # pragma: no cover - defensive
                device = None
            try:
                torch = importlib.import_module("torch")
                cuda_device_count = int(torch.cuda.device_count())
            except Exception:
                cuda_device_count = 0

        model_loaded = False
        message = self.readiness_message()
        if probe_runtime and dependency_available:
            try:
                self._get_or_create_model()
                model_loaded = True
            except Exception as exc:
                message = f"Qwen3-ASR 加载失败：{exc}"
                model_loaded = False

        raw: dict[str, Any] = {
            "model_default": _DEFAULT_MODEL,
            "language_default": self.default_language,
        }
        if missing:
            raw["missing_dependencies"] = list(missing)
            raw["suggested_fix"] = (
                "请运行：py -3 -m pip install -r backend/requirements.txt 以安装 Qwen3-ASR 依赖。"
            )

        return AsrProviderDiagnostics(
            provider="qwen3-asr",
            model=self.model_name,
            dependency_available=dependency_available,
            configured=configured,
            model_loaded=model_loaded,
            requested_device=self.requested_device,
            device=device,
            cuda_device_count=cuda_device_count,
            timeout_seconds=self.timeout_seconds,
            max_concurrency=self.max_concurrency,
            message=message,
            raw=raw,
        )

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
            return self._transcribe_audio_once(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )

        return self._run_with_timeout(_operation, timeout_seconds=float(self.timeout_seconds))

    def transcribe_audio_with_options(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        model: str | None = None,
        device: str | None = None,
        language: str | None = None,
        max_new_tokens: int | None = None,
        extra_context: str | None = None,
        use_domain_context: bool = True,
        context_prompt_override: str | None = None,
        timeout_seconds: float | None = None,
    ) -> AsrTranscriptionResult:
        if not self.is_dependency_available():
            raise AsrProviderUnavailableError(self.readiness_message())

        effective_timeout = float(timeout_seconds) if timeout_seconds is not None else float(self.timeout_seconds)

        def _operation() -> AsrTranscriptionResult:
            return self._transcribe_audio_once(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
                model=model,
                device=device,
                language=language,
                max_new_tokens=max_new_tokens,
                extra_context=extra_context,
                use_domain_context=use_domain_context,
                context_prompt_override=context_prompt_override,
            )

        return self._run_with_timeout(_operation, timeout_seconds=effective_timeout)

    # ------------------------------------------------------------------
    # Internal helpers (also used as patch points in tests)
    # ------------------------------------------------------------------
    def _build_qwen_prompt(
        self,
        *,
        processor: Any,
        language: str,
        context_prompt: str,
    ) -> str:
        """Produce the chat-template prompt fed into the Qwen processor.

        The structure mirrors the Qwen3-ASR reference implementation: a
        system message containing user-provided correction context, followed
        by an assistant turn whose body advertises the language so that the
        model emits the transcript right after :data:`QWEN_ASR_MODEL_TAG`.
        """
        language_label = (language or self.default_language).strip() or self.default_language
        context_block = (context_prompt or "").strip()
        # The first message contains both the user-supplied correction
        # context and the language marker that Qwen3-ASR expects to emit
        # the transcript right after.  Keeping everything in a single turn
        # matches the reference chat template and lets the assistant
        # produce ``...{QWEN_ASR_MODEL_TAG}<transcript>``.
        if context_block:
            user_content = f"{context_block} language {language_label}{QWEN_ASR_MODEL_TAG}"
        else:
            user_content = f"language {language_label}{QWEN_ASR_MODEL_TAG}"
        messages = [{"role": "user", "content": user_content}]
        return processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
        )

    def _parse_qwen_output(
        self,
        output_text: str,
        *,
        forced_language: str | None = None,
    ) -> tuple[str, str]:
        """Split ``output_text`` into ``(language, transcript)``.

        The model emits ``language <Lang><asr_text><transcript>`` for prompts
        produced by :meth:`_build_qwen_prompt`.  When ``forced_language`` is
        supplied we accept transcripts that already have the prefix stripped.
        """
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
            transcript = transcript.lstrip()
        else:
            transcript = transcript.lstrip()
        return language, transcript

    def _transcribe_audio_once(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        model: str | None = None,
        device: str | None = None,
        language: str | None = None,
        max_new_tokens: int | None = None,
        extra_context: str | None = None,
        use_domain_context: bool = True,
        context_prompt_override: str | None = None,
    ) -> AsrTranscriptionResult:
        """Run a single Qwen3-ASR inference pass against ``file_bytes``.

        Delegates to ``Qwen3ASRModel.transcribe(audio=(pcm_16k, 16000), ...)``
        so the chat template, tokenizer, dtype alignment and language-code
        marshalling all happen inside the vendor-maintained wrapper.
        """
        started = time.perf_counter()
        active_model_name = (model or self.model_name).strip() or self.model_name
        active_device = (device or self._resolve_device()).strip() or "cpu"
        active_language = (language or self.default_language).strip() or self.default_language

        try:
            wrapper = self._get_or_create_model(
                model_name=active_model_name,
                device=active_device,
            )
        except AsrProviderUnavailableError:
            raise
        except Exception as exc:
            raise AsrProviderUnavailableError(f"Qwen3-ASR 模型加载失败：{exc}") from exc

        context_prompt = context_prompt_override
        if context_prompt is None:
            if use_domain_context or extra_context:
                lines: list[str] = []
                if use_domain_context:
                    lines.append(
                        "请将听到的食材采购语音转写为简体中文，使用阿拉伯数字与标准单位（如：白菜4.8斤）。"
                    )
                if extra_context:
                    lines.append(extra_context.strip())
                context_prompt = " ".join(line for line in lines if line)
            else:
                context_prompt = ""

        try:
            audio_payload = self._decode_audio(
                file_bytes, filename=filename, content_type=content_type
            )
            results = wrapper.transcribe(
                audio=(audio_payload, 16_000),
                context=context_prompt or "",
                language=active_language or None,
                return_time_stamps=False,
            )
        except AsrProviderTimeoutError:
            raise
        except AsrProviderUnavailableError:
            raise
        except Exception as exc:
            raise AsrProviderUnavailableError(
                f"Qwen3-ASR 推理失败：{exc}"
            ) from exc

        if not results:
            raise AsrProviderUnavailableError("Qwen3-ASR 推理失败：未返回任何结果。")

        result = results[0]
        transcript = getattr(result, "text", "") or ""
        detected_language = getattr(result, "language", "") or ""
        duration_ms = int((time.perf_counter() - started) * 1000)

        return AsrTranscriptionResult(
            transcript=transcript,
            provider="qwen3-asr",
            model=active_model_name,
            duration_ms=duration_ms,
            raw_metadata={
                "raw_text": transcript,
                "language": detected_language or active_language,
                "device": active_device,
                "filename": filename,
                "content_type": content_type or "",
            },
        )

    def _run_with_timeout(
        self,
        operation: Callable[[], Any],
        *,
        timeout_seconds: float,
    ) -> Any:
        future = self._executor.submit(operation)
        try:
            return future.result(timeout=timeout_seconds if timeout_seconds and timeout_seconds > 0 else None)
        except FutureTimeoutError as exc:
            future.cancel()
            raise AsrProviderTimeoutError(
                f"Qwen3-ASR 推理超时（>{timeout_seconds:.1f}s）。请检查模型加载状态或换用备用通道。"
            ) from exc

    def _resolve_device(self) -> str:
        requested = (self.requested_device or "auto").lower()
        if requested in {"cpu", "cuda"} or requested.startswith("cuda:"):
            return requested
        # auto: prefer CUDA if available
        try:
            torch = importlib.import_module("torch")
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _get_or_create_model(
        self,
        *,
        model_name: str | None = None,
        device: str | None = None,
    ) -> Any:
        """Return a cached ``Qwen3ASRModel`` wrapper.

        We use the high-level wrapper from the ``qwen-asr`` package instead of
        the bare ``processor + generate`` pair: the wrapper internally handles
        the chat template, dtype alignment, language code and output parsing
        that the raw transformers classes expect in an exact but undocumented
        way. Loading the wrapper here also lets callers treat this method as a
        stable patch point in tests.
        """
        target_model = (model_name or self.model_name).strip() or self.model_name
        with self._model_lock:
            if self._model_bundle is not None:
                return self._model_bundle
            _ensure_qwen_asr_importable()
            try:
                from qwen_asr import Qwen3ASRModel
            except Exception as exc:
                raise AsrProviderUnavailableError(
                    f"Qwen3-ASR 依赖 qwen_asr 未就绪：{exc}"
                ) from exc
            try:
                wrapper = Qwen3ASRModel.from_pretrained(
                    target_model,
                    forced_aligner=None,  # skip nagisa-dependent Japanese aligner
                    max_new_tokens=int(self.max_new_tokens) or None,
                )
            except Exception as exc:
                raise AsrProviderUnavailableError(
                    f"Qwen3-ASR 模型加载失败：{exc}"
                ) from exc
            self._model_bundle = wrapper
            return self._model_bundle

    def _build_default_context_prompt(
        self,
        *,
        use_domain_context: bool,
        extra_context: str | None,
    ) -> str:
        lines: list[str] = []
        if use_domain_context:
            lines.append(
                "请将听到的食材采购语音转写为简体中文，使用阿拉伯数字与标准单位（如：白菜4.8斤）。"
            )
        if extra_context:
            lines.append(extra_context.strip())
        return " ".join(line for line in lines if line)

    def _decode_audio(
        self,
        file_bytes: bytes,
        *,
        filename: str,
        content_type: str | None,
    ) -> Any:
        """Convert an audio blob into a 16 kHz mono float32 waveform.

        The browser's MediaRecorder emits ``audio/webm;codecs=opus`` by default,
        which libsndfile cannot parse ("Format not recognised"). We try the
        fast soundfile path first for native formats (wav/flac/ogg) and fall
        back to the shared PyAV transcoder for everything else. The PyAV path
        also guarantees a 16 kHz mono layout, which the Qwen3-ASR processor
        requires.
        """
        try:
            soundfile = importlib.import_module("soundfile")
        except Exception as exc:
            raise AsrProviderUnavailableError(
                f"Qwen3-ASR 需要 soundfile 解码音频，未安装：{exc}"
            ) from exc

        # Fast path: native libsndfile format (already WAV/FLAC/OGG).
        try:
            with io.BytesIO(file_bytes) as buf:
                waveform, sample_rate = soundfile.read(buf, dtype="float32")
            if sample_rate == 16_000 and getattr(waveform, "ndim", 1) == 1:
                return waveform
        except Exception:
            waveform = None
            sample_rate = 0

        # Fallback: write to a temp file, transcode via PyAV into a normalised
        # 16 kHz mono WAV, then read back.
        import tempfile
        import os as _os

        suffix = _guess_audio_suffix(filename, content_type)
        tmp_in = tempfile.NamedTemporaryFile(
            prefix="qwen3-asr-", suffix=suffix, delete=False
        )
        try:
            tmp_in.write(file_bytes)
            tmp_in.close()
            normalised_path = self._convert_to_wav_via_pyav(tmp_in.name)
            with open(normalised_path, "rb") as handle:
                waveform, sample_rate = soundfile.read(handle, dtype="float32")
        except Exception as exc:
            raise AsrProviderUnavailableError(
                f"Qwen3-ASR 音频解码失败（格式 {suffix or content_type or '?'}）：{exc}"
            ) from exc
        finally:
            for path in {tmp_in.name, locals().get("normalised_path")}:
                if path and _os.path.exists(path):
                    try:
                        _os.remove(path)
                    except OSError:
                        pass
        return waveform

    def _convert_to_wav_via_pyav(self, input_path: str) -> str:
        """Best-effort audio normaliser for Qwen3-ASR.

        If the file is already a WAV that ``soundfile`` can read natively we
        return the original path (the processor can consume it directly).
        Otherwise we transcode via PyAV into ``<input>.converted.wav`` at the
        canonical 16 kHz mono layout the Qwen3-ASR processor expects.
        """
        if soundfile_can_read(input_path):
            return input_path
        output_path = f"{input_path}.converted.wav"
        return convert_to_normalized_wav(input_path, output_path=output_path)

    def _move_to_device(self, inputs: Any, device: str) -> Any:
        try:
            if hasattr(inputs, "to"):
                return inputs.to(device)
        except Exception:
            return inputs
        return inputs

    def _align_inputs_to_model_dtype(self, inputs: Any, model: Any) -> Any:
        """Cast floating-point input tensors to the model's dtype.

        ``torch_dtype="auto"`` often loads Qwen3-ASR in bfloat16/float16; the
        processor still returns float32 audio features which makes the audio
        encoder's ``Conv1d`` fail with "Input type (float) and bias type
        (struct c10::BFloat16) should be the same". Cast all floating-point
        tensors in the inputs dict to ``model.dtype``; leave int/long tensors
        (``input_ids``, ``attention_mask``, ...) untouched.
        """
        target_dtype = getattr(model, "dtype", None)
        if target_dtype is None:
            return inputs
        try:
            import torch  # local import keeps the optional dependency lazy
        except Exception:
            return inputs

        def _cast(value: Any) -> Any:
            if isinstance(value, torch.Tensor) and value.is_floating_point():
                if value.dtype != target_dtype:
                    return value.to(target_dtype)
            return value

        # ``BatchFeature`` / ``BatchEncoding`` behave like dicts but we keep
        # the original container so downstream ``**inputs`` unpacking works.
        try:
            data = getattr(inputs, "data", None)
            if isinstance(data, dict):
                for key, value in list(data.items()):
                    data[key] = _cast(value)
                return inputs
            if isinstance(inputs, dict):
                for key, value in list(inputs.items()):
                    inputs[key] = _cast(value)
                return inputs
        except Exception:
            pass
        return inputs

    # ------------------------------------------------------------------
    # Dependency probing
    # ------------------------------------------------------------------
    def _collect_missing_dependencies(self) -> list[str]:
        missing: list[str] = []
        for dist_name, module_name in _REQUIRED_DEPENDENCIES:
            if not self._is_dependency_present(dist_name, module_name):
                missing.append(dist_name)
        return missing

    def _is_dependency_present(self, dist_name: str, module_name: str) -> bool:
        # A dependency is considered present only when both the pip
        # distribution metadata AND the importable module spec exist.
        # Tests rely on this strict policy because Qwen3-ASR has known
        # cases of orphaned distribution stubs without an actual module
        # (or vice-versa) that should still surface as unavailable.
        if not self._get_distribution_version(dist_name):
            return False
        if importlib.util.find_spec(module_name) is None:
            return False
        return True

    def _get_distribution_version(self, package_name: str) -> str | None:
        try:
            return importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            return None
        except Exception:
            return None

    def _get_module_version(self, module_name: str) -> str | None:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            return None
        version = getattr(module, "__version__", None)
        return str(version) if version else None

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        raw = os.getenv(name)
        if raw is None:
            return float(default)
        try:
            return float(str(raw).strip())
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _env_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return int(default)
        try:
            return int(float(str(raw).strip()))
        except (TypeError, ValueError):
            return int(default)
