# Qwen3-ASR Lab

This directory contains an isolated ASR test page mounted at `/tests/funasr-lab`.

The route path is kept unchanged so the existing launcher still works, but the lab
now uses `Qwen/Qwen3-ASR-1.7B` through the Transformers backend.

## Endpoints

- Page: `/tests/funasr-lab`
- Status: `/api/test/funasr-lab/status`
- Transcribe: `/api/test/funasr-lab/transcribe`
- Lexicon status: `/api/test/funasr-lab/lexicon`
- Confirm correction: `/api/test/funasr-lab/lexicon/confirm`
- Apply confirmed corrections: `/api/test/funasr-lab/lexicon/apply-incremental`
- Export text-only training pack: `/api/test/funasr-lab/lexicon/export-training-pack`

## Correction lexicon

The lab separates human seed words from machine-owned incremental corrections.

- `config/funasr_lab_hotwords.jsonc` is a read-only seed file for manual words and
  known correction pairs.
- `data/asr_corrections/funasr_lab_corrections.json` is created at runtime for
  pending, confirmed, active, and disabled corrections.
- Parsed ASR results create pending candidates only. They do not affect the prompt
  until the user confirms them and clicks **Apply Incremental Lexicon**.
- Applying the incremental lexicon updates the next Qwen3-ASR context prompt. It
  does not train or fine-tune model weights.
- **Export Training Pack** writes confirmed and active corrections to JSONL for
  later analysis or cloud training preparation. By default the export is
  text-only and does not include `audio_path` or `audio_ref`.
- Audio retention is opt-in per transcription. If **Retain this audio locally for
  future training export** is enabled, the lab stores the clip under
  `data/asr_corrections/audio/` and the JSONL export includes an `audio_ref`
  relative to that directory. Nothing is uploaded automatically.
- Active corrections are also used by the main faster-whisper STT service as
  prompt/hotword context. Set `DAILY_INTAKE_STT_USE_ASR_CORRECTIONS=false` to
  disable this sharing for the formal STT path.

## Environment notes

- Windows 11
- Python 3.11
- CUDA-enabled PyTorch is recommended for `Qwen3-ASR-1.7B`
- The current machine is `RTX 2070 8GB`, so the lab is configured conservatively
  and should be treated as a single-user test flow

## Install

```powershell
python -m pip install -r backend/funasr_lab/requirements.txt
```

The lab forces Hugging Face cache into the project `.cache/huggingface` directory
so it does not fall back to a small `C:` drive cache.

## Important limitation

The upstream `qwen-asr` package currently imports the forced-aligner stack on import.
In this workspace, that path fails because `nagisa` does not initialize cleanly in the
current environment. The lab therefore loads only the Qwen3-ASR Transformers backend
modules and does not enable forced alignment or timestamps.
