from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.env import load_project_env
from backend.services.speech_to_text_service import (
    SpeechToTextConfigError,
    SpeechToTextError,
    SpeechToTextService,
)


DEFAULT_MODES = (
    ("cpu", "int8"),
    ("cuda", "float16"),
    ("cuda", "int8_float16"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark local daily-intake STT across CPU/GPU modes using the same audio file."
    )
    parser.add_argument("audio_path", help="Path to a local audio file such as .wav/.webm/.m4a")
    parser.add_argument(
        "--mode",
        action="append",
        dest="modes",
        help="Benchmark mode in the form device:compute_type. Can be repeated.",
    )
    parser.add_argument(
        "--json-out",
        dest="json_out",
        help="Optional path to write benchmark results as JSON.",
    )
    return parser.parse_args()


def parse_modes(raw_modes: list[str] | None) -> list[tuple[str, str]]:
    if not raw_modes:
        return list(DEFAULT_MODES)

    parsed: list[tuple[str, str]] = []
    for raw_mode in raw_modes:
        device, separator, compute_type = str(raw_mode or "").partition(":")
        if not separator or not device.strip() or not compute_type.strip():
            raise ValueError(f"Invalid mode '{raw_mode}'. Expected device:compute_type.")
        parsed.append((device.strip().lower(), compute_type.strip().lower()))
    return parsed


@contextmanager
def temporary_stt_env(device: str, compute_type: str):
    keys = ("DAILY_INTAKE_STT_DEVICE", "DAILY_INTAKE_STT_COMPUTE_TYPE")
    original = {key: os.environ.get(key) for key in keys}
    os.environ["DAILY_INTAKE_STT_DEVICE"] = device
    os.environ["DAILY_INTAKE_STT_COMPUTE_TYPE"] = compute_type
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def benchmark_mode(audio_path: Path, *, device: str, compute_type: str) -> dict[str, object]:
    file_bytes = audio_path.read_bytes()
    content_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"

    with temporary_stt_env(device, compute_type):
        service = SpeechToTextService()

        warmup_started = time.perf_counter()
        warmup_message = service.warmup_model()
        warmup_seconds = time.perf_counter() - warmup_started

        runtime = service.runtime_status()

        transcribe_started = time.perf_counter()
        result = service.transcribe_audio(
            file_bytes=file_bytes,
            filename=audio_path.name,
            content_type=content_type,
        )
        transcribe_seconds = time.perf_counter() - transcribe_started

    return {
        "requested_device": device,
        "requested_compute_type": compute_type,
        "effective_device": runtime.device,
        "effective_compute_type": runtime.compute_type,
        "fallback_used": runtime.fallback_used,
        "fallback_reason": runtime.fallback_reason,
        "warmup_seconds": round(warmup_seconds, 3),
        "transcribe_seconds": round(transcribe_seconds, 3),
        "transcript": result.transcript,
        "transcript_length": len(result.transcript),
        "model": result.model,
        "warmup_message": warmup_message,
    }


def print_summary(audio_path: Path, results: list[dict[str, object]]) -> None:
    print(f"Audio sample: {audio_path}")
    print("")
    header = (
        f"{'Mode':<22}"
        f"{'Effective':<22}"
        f"{'Warmup(s)':>12}"
        f"{'Transcribe(s)':>15}"
        f"{'Fallback':>11}"
    )
    print(header)
    print("-" * len(header))

    for row in results:
        requested = f"{row['requested_device']}/{row['requested_compute_type']}"
        effective = f"{row['effective_device']}/{row['effective_compute_type']}"
        warmup_value = "-" if row["warmup_seconds"] is None else str(row["warmup_seconds"])
        transcribe_value = "-" if row["transcribe_seconds"] is None else str(row["transcribe_seconds"])
        print(
            f"{requested:<22}"
            f"{effective:<22}"
            f"{warmup_value:>12}"
            f"{transcribe_value:>15}"
            f"{str(row['fallback_used']):>11}"
        )

    print("")
    for row in results:
        print(f"[{row['requested_device']}/{row['requested_compute_type']}]")
        print(f"Transcript: {row['transcript']}")
        if row["fallback_reason"]:
            print(f"Fallback reason: {row['fallback_reason']}")
        print("")


def main() -> int:
    load_project_env()
    args = parse_args()

    audio_path = Path(args.audio_path).expanduser().resolve()
    if not audio_path.exists() or not audio_path.is_file():
        print(f"Audio file not found: {audio_path}")
        return 1

    try:
        modes = parse_modes(args.modes)
    except ValueError as exc:
        print(str(exc))
        return 1

    results: list[dict[str, object]] = []
    for device, compute_type in modes:
        print(f"Running benchmark for {device}/{compute_type} ...")
        try:
            results.append(
                benchmark_mode(audio_path, device=device, compute_type=compute_type)
            )
        except (SpeechToTextConfigError, SpeechToTextError) as exc:
            results.append(
                {
                    "requested_device": device,
                    "requested_compute_type": compute_type,
                    "effective_device": None,
                    "effective_compute_type": None,
                    "fallback_used": False,
                    "fallback_reason": str(exc),
                    "warmup_seconds": None,
                    "transcribe_seconds": None,
                    "transcript": "",
                    "transcript_length": 0,
                    "model": None,
                    "warmup_message": "",
                }
            )
        except Exception as exc:  # pragma: no cover - external runtime path
            results.append(
                {
                    "requested_device": device,
                    "requested_compute_type": compute_type,
                    "effective_device": None,
                    "effective_compute_type": None,
                    "fallback_used": False,
                    "fallback_reason": f"Unexpected error: {exc}",
                    "warmup_seconds": None,
                    "transcribe_seconds": None,
                    "transcript": "",
                    "transcript_length": 0,
                    "model": None,
                    "warmup_message": "",
                }
            )

    print("")
    print_summary(audio_path, results)

    if args.json_out:
        output_path = Path(args.json_out).expanduser().resolve()
        output_path.write_text(
            json.dumps(
                {
                    "audio_path": str(audio_path),
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"JSON report written to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
