from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.env import load_project_env
from backend.services.speech_to_text_service import SpeechToTextService


def main() -> int:
    load_project_env()
    service = SpeechToTextService()

    diagnostics = service.diagnostics(probe_runtime=True)
    if not diagnostics.model_loaded:
        print(f"Local STT warmup failed: {diagnostics.message}")
        return 1

    print("Local STT warmup OK")
    print(diagnostics.message)
    print(f"Requested device: {diagnostics.requested_device}")
    print(f"Requested compute type: {diagnostics.requested_compute_type}")
    print(f"Resolved device: {diagnostics.resolved_device}")
    print(f"Resolved compute type: {diagnostics.resolved_compute_type}")
    print(f"Effective device: {diagnostics.effective_device}")
    print(f"Effective compute type: {diagnostics.effective_compute_type}")
    print(f"CUDA device count: {diagnostics.cuda_device_count}")
    print(f"CPU compute types: {', '.join(diagnostics.supported_compute_types_cpu) or '-'}")
    print(f"CUDA compute types: {', '.join(diagnostics.supported_compute_types_cuda) or '-'}")
    print(f"Missing CUDA DLLs: {', '.join(diagnostics.missing_cuda_runtime_dlls) or '-'}")
    print(f"Fallback used: {diagnostics.fallback_used}")
    if diagnostics.fallback_reason:
        print(f"Fallback reason: {diagnostics.fallback_reason}")
    if diagnostics.suggested_fix:
        print(f"Suggested fix: {diagnostics.suggested_fix}")
    print(f"Bundled DLL dir: {service.bundled_dll_directories[0]}")
    print(f"Model cache: {service.download_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
