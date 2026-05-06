"""Audio preprocessing helpers shared by both ASR providers.

The daily-intake flow records short voice clips in arbitrary browser formats
(.webm, .ogg, .mp3, sometimes mis-named .wav).  Both faster-whisper and
Qwen3-ASR prefer a normalised 16 kHz mono PCM WAV, so we centralise the
decode + resample + normalise pipeline here.

The functions fall back gracefully: soundfile is the fast path for already
conforming WAV files, PyAV handles everything else.  Silent inputs stay
silent (they should surface as "no speech" downstream) but quiet inputs are
peak-normalised so the ASR model has a chance to pick up the content.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable

import numpy as np

_logger = logging.getLogger(__name__)

_TARGET_SAMPLE_RATE = 16_000
_PEAK_TARGET = 0.3
_SILENCE_PEAK_THRESHOLD = 1e-3


def convert_to_normalized_wav(
    input_path: str,
    *,
    output_path: str,
    target_sample_rate: int = _TARGET_SAMPLE_RATE,
) -> str:
    """Decode ``input_path`` to a normalised mono WAV at ``target_sample_rate``.

    The output is written to ``output_path`` and that path is returned.  The
    caller decides the filename convention (faster-whisper uses
    ``<src>.wav``; Qwen3-ASR uses ``<src>.converted.wav``).
    """
    samples, sample_rate = _decode_audio(input_path)
    samples = _to_mono(samples)
    if sample_rate != target_sample_rate and samples.size:
        samples = _resample_linear(samples, sample_rate, target_sample_rate)
        sample_rate = target_sample_rate
    samples = _peak_normalize(samples)
    _write_pcm16_wav(output_path, samples, sample_rate)
    return output_path


def soundfile_can_read(path: str) -> bool:
    try:
        import soundfile as sf  # local import to keep module import cheap
    except Exception:
        return False
    try:
        with sf.SoundFile(path):
            return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _decode_audio(path: str) -> tuple[np.ndarray, int]:
    # Fast path: soundfile (libsndfile) handles standard WAV / FLAC / OGG.
    try:
        import soundfile as sf

        samples, sample_rate = sf.read(path, dtype="float32", always_2d=False)
        return np.asarray(samples, dtype=np.float32), int(sample_rate)
    except Exception as sf_err:
        _logger.debug("soundfile failed on %s (%s) – falling back to PyAV", path, sf_err)

    # Fallback: PyAV handles arbitrary browser/container formats.
    try:
        import av  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            f"Neither soundfile nor PyAV could decode the audio file {path!r}: {exc}"
        ) from exc

    collected: list[np.ndarray] = []
    sample_rate = 0
    with av.open(path) as container:  # type: ignore[attr-defined]
        audio_streams = [s for s in container.streams if s.type == "audio"]
        if not audio_streams:
            raise RuntimeError(f"No audio streams found in {path!r}")
        stream = audio_streams[0]
        sample_rate = int(getattr(stream, "rate", 0) or 0)
        for frame in container.decode(stream):
            array = frame.to_ndarray()
            collected.append(array)
    if not collected:
        return np.zeros(0, dtype=np.float32), sample_rate or _TARGET_SAMPLE_RATE

    stacked = np.concatenate([_flatten_frame(a) for a in collected], axis=-1)
    stacked = _to_float32(stacked)
    return stacked, sample_rate or _TARGET_SAMPLE_RATE


def _flatten_frame(array: np.ndarray) -> np.ndarray:
    if array.ndim == 1:
        return array
    # PyAV packs planar audio as (channels, samples); interleaved as (1, n)
    if array.shape[0] <= 2:
        return array.reshape(-1, order="F")
    return array.reshape(-1)


def _to_float32(array: np.ndarray) -> np.ndarray:
    if array.dtype == np.float32 or array.dtype == np.float64:
        return array.astype(np.float32, copy=False)
    # Integer PCM samples – scale by max-value of the dtype.
    info = np.iinfo(array.dtype)
    scale = float(max(abs(info.min), abs(info.max))) or 1.0
    return (array.astype(np.float32) / scale).astype(np.float32)


def _to_mono(samples: np.ndarray) -> np.ndarray:
    if samples.ndim <= 1:
        return samples.astype(np.float32, copy=False)
    return samples.mean(axis=-1 if samples.shape[-1] < samples.shape[0] else 0).astype(
        np.float32, copy=False
    )


def _resample_linear(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate <= 0 or target_rate <= 0 or source_rate == target_rate:
        return samples
    new_length = int(round(len(samples) * target_rate / source_rate))
    if new_length <= 0:
        return np.zeros(0, dtype=np.float32)
    indices = np.linspace(0, len(samples) - 1, new_length, dtype=np.float64)
    return np.interp(indices, np.arange(len(samples)), samples).astype(np.float32)


def _peak_normalize(samples: np.ndarray) -> np.ndarray:
    if samples.size == 0:
        return samples
    peak = float(np.max(np.abs(samples)))
    if peak <= _SILENCE_PEAK_THRESHOLD:
        return samples.astype(np.float32, copy=False)
    gain = _PEAK_TARGET / peak
    return (samples * gain).astype(np.float32, copy=False)


def _write_pcm16_wav(path: str, samples: np.ndarray, sample_rate: int) -> None:
    import soundfile as sf

    parent = Path(path).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    # Clip before quantising to avoid int16 overflow.
    clipped = np.clip(samples, -1.0, 1.0).astype(np.float32)
    sf.write(path, clipped, int(sample_rate or _TARGET_SAMPLE_RATE), subtype="PCM_16")
