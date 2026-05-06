"""
Test the audio preprocessing pipeline for both ASR providers.
  Run with: .venv-win10/Scripts/python.exe tests/test_audio_pipeline.py
"""
import sys
import os
import tempfile
import wave
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def make_sine_wav(path: str, freq: float = 440.0, duration: float = 2.0, sr: int = 16000, amp: float = 0.5):
    """Write a sine-wave WAV file (simulates real speech signal)."""
    import math
    import struct
    n = int(sr * duration)
    frames = struct.pack("<" + "h" * n, *[
        int(amp * 32767 * math.sin(2 * math.pi * freq * i / sr))
        for i in range(n)
    ])
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(frames)


def make_silent_wav(path: str, duration: float = 2.0, sr: int = 16000):
    """Write a silent WAV file (all zeros)."""
    n = int(sr * duration)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * n)


def make_quiet_wav(path: str, duration: float = 2.0, sr: int = 16000, amp: float = 0.002):
    """Write a very quiet sine WAV (simulates low microphone volume)."""
    make_sine_wav(path, amp=amp, duration=duration, sr=sr)


PASS = 0
FAIL = 0


def check(condition: bool, label: str):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label}")
        FAIL += 1


# ─── Test 1: faster-whisper path ─────────────────────────────────────────────
print("\n=== Test 1: SpeechToTextService._convert_to_wav_via_pyav ===")
from backend.services.speech_to_text_service import SpeechToTextService

svc = SpeechToTextService.__new__(SpeechToTextService)

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    sine_path = f.name
make_sine_wav(sine_path, amp=0.5)

out = svc._convert_to_wav_via_pyav(sine_path)
check(out == sine_path + ".wav", "converted path has .wav suffix")
check(os.path.exists(out), "output WAV exists")

import soundfile as sf
import numpy as np
samples, sr = sf.read(out)
rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
check(sr == 16000, f"sample rate is 16000 (got {sr})")
check(rms > 0.01, f"RMS is non-trivial after normal audio: {rms:.4f}")

for p in (sine_path, out):
    try: os.remove(p)
    except OSError: pass

# ─── Test 2: quiet audio normalization ────────────────────────────────────────
print("\n=== Test 2: Quiet audio normalization ===")

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    quiet_path = f.name
make_quiet_wav(quiet_path, amp=0.002)

out = svc._convert_to_wav_via_pyav(quiet_path)
samples, sr = sf.read(out)
rms_out = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
check(rms_out > 0.05, f"quiet audio was amplified by normalization: RMS={rms_out:.4f} (target 0.1)")

for p in (quiet_path, out):
    try: os.remove(p)
    except OSError: pass

# ─── Test 3: silent audio detection ──────────────────────────────────────────
print("\n=== Test 3: Silent audio detection (logs a warning, no crash) ===")

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    silent_path = f.name
make_silent_wav(silent_path)

out = svc._convert_to_wav_via_pyav(silent_path)
check(os.path.exists(out), "output WAV created even for silent audio")
samples, sr = sf.read(out)
rms_out = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
check(rms_out < 0.001, f"silent audio stays silent (no fake amplification): RMS={rms_out:.8f}")

for p in (silent_path, out):
    try: os.remove(p)
    except OSError: pass

# ─── Test 4: Qwen3-ASR path ──────────────────────────────────────────────────
print("\n=== Test 4: Qwen3AsrProvider._convert_to_wav_via_pyav ===")
from backend.services.qwen3_asr_provider import Qwen3AsrProvider

qwen = Qwen3AsrProvider.__new__(Qwen3AsrProvider)

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    sine_path = f.name
make_sine_wav(sine_path, freq=250.0, amp=0.3)

out = qwen._convert_to_wav_via_pyav(sine_path)
# soundfile can open WAV directly so _convert_to_wav_via_pyav returns the original path
check(os.path.exists(out), "Qwen3-ASR output path exists")
check(out in (sine_path, sine_path + ".converted.wav"), "Qwen3-ASR output is original or converted WAV")

samples, sr = sf.read(out)
rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))
check(sr == 16000, f"Qwen3-ASR output sample rate 16000 (got {sr})")
check(rms > 0.01, f"Qwen3-ASR RMS is non-trivial: {rms:.4f}")

for p in (sine_path, out):
    try: os.remove(p)
    except OSError: pass

# ─── Test 5: non-WAV file (soundfile will fail, PyAV should handle) ───────────
print("\n=== Test 5: soundfile-unsupported format fallback ===")

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    sine_path = f.name
make_sine_wav(sine_path, freq=300.0, amp=0.4)

# Rename to .webm so soundfile will reject it (content is actually WAV but extension is wrong)
import shutil
fake_webm = sine_path.replace(".wav", ".webm")
shutil.copy(sine_path, fake_webm)

out_svc = svc._convert_to_wav_via_pyav(fake_webm)
out_qwen = qwen._convert_to_wav_via_pyav(fake_webm)

# PyAV can read WAV content regardless of extension
for label, out in [("svc", out_svc), ("qwen", out_qwen)]:
    check(os.path.exists(out), f"{label}: output exists for misnamed .webm")

for p in (sine_path, fake_webm, out_svc, out_qwen):
    try: os.remove(p)
    except OSError: pass

# ─── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
