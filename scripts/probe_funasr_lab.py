from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.env import load_project_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a single end-to-end FunASR lab transcription probe with explicit "
            "stage timings, WAV conversion, and a hard timeout."
        )
    )
    parser.add_argument(
        "audio_path",
        nargs="?",
        help="Optional audio path. Defaults to the smallest sample under recorder/.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Hard timeout in seconds for the actual FunASR transcription step.",
    )
    parser.add_argument(
        "--ffmpeg-timeout",
        type=int,
        default=30,
        help="Timeout in seconds for audio conversion to WAV.",
    )
    parser.add_argument(
        "--json-out",
        help="Optional path to write the final probe result as JSON.",
    )
    parser.add_argument(
        "--mode",
        choices=("service", "direct"),
        default="direct",
        help="Probe via the service wrapper or by explicitly timing model load and generate.",
    )
    parser.add_argument(
        "--use-local-cache",
        action="store_true",
        help="Use locally cached ModelScope model directories instead of named model refs.",
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--result-file",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--trace-file",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--worker-mode",
        choices=("service", "direct"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--worker-local-cache",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def log(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def choose_audio_path(raw_audio_path: str | None) -> Path:
    if raw_audio_path:
        audio_path = Path(raw_audio_path).expanduser().resolve()
        if not audio_path.exists() or not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        return audio_path

    samples = sorted((ROOT_DIR / "recorder").glob("*.*"), key=lambda path: path.stat().st_size)
    for sample in samples:
        if sample.suffix.lower() in {".wav", ".m4a", ".mp3", ".webm", ".ogg"}:
            return sample.resolve()

    raise FileNotFoundError("No supported audio samples found under recorder/")


def convert_to_wav(audio_path: Path, *, timeout_seconds: int) -> tuple[Path, Path | None]:
    temp_root = ROOT_DIR / ".runtime" / "funasr-probe"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="wav-", dir=temp_root))
    wav_path = temp_dir / "probe.wav"

    if audio_path.suffix.lower() == ".wav":
        shutil.copyfile(audio_path, wav_path)
        log("Input is already WAV; copied to ASCII staging path")
        return wav_path, temp_dir

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise FileNotFoundError("ffmpeg is required for non-WAV samples but was not found in PATH.")

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(audio_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(wav_path),
    ]
    log(f"Converting to WAV via ffmpeg: {audio_path.name} -> {wav_path.name}")
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        timeout=timeout_seconds,
    )
    elapsed = time.perf_counter() - started
    log(f"WAV conversion finished in {elapsed:.2f}s")

    if completed.returncode != 0 or not wav_path.exists():
        stderr = (completed.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg conversion failed: {stderr or 'unknown error'}")

    return wav_path, temp_dir


def append_trace(trace_file: Path | None, message: str) -> None:
    if trace_file is None:
        return
    timestamp = time.strftime("%H:%M:%S")
    with trace_file.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def resolve_model_refs(*, use_local_cache: bool) -> tuple[str, str | None]:
    if not use_local_cache:
        return ("paraformer-zh", "fsmn-vad")

    cache_root = Path.home() / ".cache" / "modelscope" / "hub" / "models" / "iic"
    model_dir = cache_root / "speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch"
    vad_dir = cache_root / "speech_fsmn_vad_zh-cn-16k-common-pytorch"
    if model_dir.exists() and vad_dir.exists():
        return (str(model_dir), str(vad_dir))
    return ("paraformer-zh", "fsmn-vad")


def run_worker_mode(
    audio_path: Path,
    result_file: Path | None,
    trace_file: Path | None,
    *,
    mode: str,
    use_local_cache: bool,
) -> int:
    try:
        append_trace(trace_file, "worker started")
        load_project_env()
        append_trace(trace_file, "project env loaded")

        from backend.funasr_lab.service import FunASRLabConfig, FunASRLabService
        append_trace(trace_file, "funasr service imports loaded")

        service = FunASRLabService()
        append_trace(trace_file, "FunASRLabService constructed")
        status = service.status()
        append_trace(trace_file, f"service status resolved: {status['defaults']['device']}")
        file_bytes = audio_path.read_bytes()
        append_trace(trace_file, f"audio bytes loaded: {len(file_bytes)}")
        model_ref, vad_ref = resolve_model_refs(use_local_cache=use_local_cache)
        append_trace(trace_file, f"model_ref={model_ref}")
        append_trace(trace_file, f"vad_ref={vad_ref}")
        config = FunASRLabConfig(
            model=model_ref,
            vad_model=vad_ref,
            punc_model=None,
            hub="ms",
            device="auto",
            batch_size_s=300,
        )
        started = time.perf_counter()
        if mode == "service":
            append_trace(trace_file, "calling transcribe_audio")
            result = service.transcribe_audio(
                config=config,
                file_bytes=file_bytes,
                filename=audio_path.name,
                content_type="audio/wav",
            )
            append_trace(trace_file, "transcribe_audio returned")
            config_device = result["config"]["device"]
            model_name = result["funasr"]["model"]
            transcript = result["funasr"]["transcript"]
            model_load_seconds = None
            generate_seconds = None
        else:
            append_trace(trace_file, "calling _get_or_create_model")
            model_load_started = time.perf_counter()
            model = service._get_or_create_model(config)
            model_load_seconds = round(time.perf_counter() - model_load_started, 3)
            append_trace(trace_file, "model loaded")

            append_trace(trace_file, "calling model.generate")
            generate_started = time.perf_counter()
            raw_result = model.generate(
                input=str(audio_path),
                batch_size_s=max(int(config.batch_size_s or 300), 1),
                hotword=(config.hotword or "").strip() or None,
            )
            generate_seconds = round(time.perf_counter() - generate_started, 3)
            append_trace(trace_file, "model.generate returned")

            transcript = service._extract_text(raw_result)
            config_device = service._resolve_device(config.device)
            model_name = config.model
        elapsed = time.perf_counter() - started
        payload = {
            "ok": True,
            "mode": mode,
            "transcribe_seconds": round(elapsed, 3),
            "model_load_seconds": model_load_seconds,
            "generate_seconds": generate_seconds,
            "status_device": status["defaults"]["device"],
            "dependency_available": status["dependency_available"],
            "config_device": config_device,
            "model": model_name,
            "transcript": transcript,
        }
    except Exception as exc:  # pragma: no cover - runtime path
        append_trace(trace_file, f"worker exception: {type(exc).__name__}: {exc}")
        payload = {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    if result_file is not None:
        result_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("__FUNASR_RESULT__" + json.dumps(payload, ensure_ascii=False), flush=True)
    return 0 if payload.get("ok") else 1
def run_transcription_with_timeout(
    audio_path: Path,
    *,
    timeout_seconds: int,
    mode: str,
    use_local_cache: bool,
) -> dict[str, object]:
    log(f"Starting FunASR transcription worker with {timeout_seconds}s timeout")
    runtime_root = ROOT_DIR / ".runtime" / "funasr-probe"
    runtime_root.mkdir(parents=True, exist_ok=True)
    result_path = runtime_root / "probe-result.json"
    log_path = runtime_root / "probe-worker.log"
    trace_path = runtime_root / "probe-worker.trace"
    result_path.unlink(missing_ok=True)
    log_path.unlink(missing_ok=True)
    trace_path.unlink(missing_ok=True)

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        str(audio_path),
        "--result-file",
        str(result_path),
        "--trace-file",
        str(trace_path),
        "--worker-mode",
        mode,
    ]
    if use_local_cache:
        command.append("--worker-local-cache")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    with log_path.open("wb") as log_file:
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
        )
        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            if result_path.exists():
                break
            if process.poll() is not None:
                break
            time.sleep(0.5)

        if not result_path.exists():
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            worker_output = log_path.read_text(encoding="utf-8", errors="replace").strip()
            worker_trace = trace_path.read_text(encoding="utf-8", errors="replace").strip()
            raise TimeoutError(
                f"FunASR transcription exceeded {timeout_seconds}s and was terminated.\n"
                f"Worker trace:\n{worker_trace}\n"
                f"Worker log:\n{worker_output}"
            )

        payload = json.loads(result_path.read_text(encoding="utf-8"))
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if not payload.get("ok"):
            raise RuntimeError(f"{payload.get('error_type')}: {payload.get('error')}")
        return payload


def main() -> int:
    args = parse_args()
    if args.worker:
        if not args.audio_path:
            print("__FUNASR_RESULT__" + json.dumps({"ok": False, "error_type": "ValueError", "error": "Missing audio path"}))
            return 1
        result_file = Path(args.result_file).expanduser().resolve() if args.result_file else None
        trace_file = Path(args.trace_file).expanduser().resolve() if args.trace_file else None
        worker_mode = args.worker_mode or "direct"
        return run_worker_mode(
            Path(args.audio_path).expanduser().resolve(),
            result_file,
            trace_file,
            mode=worker_mode,
            use_local_cache=args.worker_local_cache,
        )

    load_project_env()

    temp_dir: Path | None = None
    started = time.perf_counter()

    try:
        audio_path = choose_audio_path(args.audio_path)
        log(f"Selected audio sample: {audio_path.name}")
        log(f"Original size: {audio_path.stat().st_size} bytes")

        wav_path, temp_dir = convert_to_wav(audio_path, timeout_seconds=args.ffmpeg_timeout)
        log(f"Converted WAV path: {wav_path}")

        result = run_transcription_with_timeout(
            wav_path,
            timeout_seconds=args.timeout,
            mode=args.mode,
            use_local_cache=args.use_local_cache,
        )
        total_seconds = round(time.perf_counter() - started, 3)

        summary = {
            "sample_name": audio_path.name,
            "source_path": str(audio_path),
            "wav_path": str(wav_path),
            "mode": result["mode"],
            "status_device": result["status_device"],
            "config_device": result["config_device"],
            "dependency_available": result["dependency_available"],
            "model": result["model"],
            "transcript": result["transcript"],
            "model_load_seconds": result["model_load_seconds"],
            "generate_seconds": result["generate_seconds"],
            "transcribe_seconds": result["transcribe_seconds"],
            "total_seconds": total_seconds,
        }

        log("FunASR probe completed successfully")
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        if args.json_out:
            output_path = Path(args.json_out).expanduser().resolve()
            output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"JSON report written to {output_path}")

        return 0
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
