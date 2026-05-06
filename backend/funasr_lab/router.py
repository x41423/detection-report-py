from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.funasr_lab.service import FunASRLabConfig, FunASRLabError, FunASRLabService

router = APIRouter()
service = FunASRLabService()
LAB_DIR = Path(__file__).resolve().parent


class FunASRLabTrackingRecordRequest(BaseModel):
    intake_date: str
    raw_name: str
    normalized_name: str
    unit: str
    quantity: float
    category: str | None = None
    transcript: str | None = None
    source: str = "funasr-lab"


class FunASRLabLexiconCandidateRequest(BaseModel):
    alias: str
    canonical_name: str
    unit: str
    raw_transcript: str | None = None
    corrected_transcript: str | None = None
    source: str = "qwen3-asr-lab"


class FunASRLabLexiconIdsRequest(BaseModel):
    ids: list[str]


class FunASRLabLexiconApplyRequest(BaseModel):
    scope: str = "all_confirmed"
    ids: list[str] | None = None


class FunASRLabLexiconDisableRequest(BaseModel):
    ids: list[str]
    reason: str | None = None


class FunASRLabLexiconExportRequest(BaseModel):
    statuses: list[str] | None = None
    ids: list[str] | None = None


def _to_bool(value: str | None, *, default: bool = False) -> bool:
    candidate = str(value or "").strip().lower()
    if not candidate:
        return default
    return candidate in {"1", "true", "yes", "on"}


@router.get("/tests/funasr-lab", include_in_schema=False)
def get_funasr_lab_page():
    return FileResponse(LAB_DIR / "page.html", media_type="text/html")


@router.get("/tests/funasr-lab/app.js", include_in_schema=False)
def get_funasr_lab_script():
    return FileResponse(LAB_DIR / "app.js", media_type="application/javascript")


@router.get("/tests/funasr-lab/styles.css", include_in_schema=False)
def get_funasr_lab_styles():
    return FileResponse(LAB_DIR / "styles.css", media_type="text/css")


@router.get("/api/test/funasr-lab/status")
def get_funasr_lab_status():
    return service.status()


@router.get("/api/test/funasr-lab/tracking")
def get_funasr_lab_tracking(
    intake_date: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=30),
):
    return service.tracking_status(intake_date=intake_date, days=days)


@router.get("/api/test/funasr-lab/lexicon")
def get_funasr_lab_lexicon():
    return service.lexicon_status(include_entries=True)


@router.post("/api/test/funasr-lab/lexicon/candidates")
def create_funasr_lab_lexicon_candidate(req: FunASRLabLexiconCandidateRequest):
    try:
        return service.create_lexicon_candidate(
            alias=req.alias,
            canonical_name=req.canonical_name,
            unit=req.unit,
            raw_transcript=req.raw_transcript,
            corrected_transcript=req.corrected_transcript,
            source=req.source,
        )
    except FunASRLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/test/funasr-lab/lexicon/confirm")
def confirm_funasr_lab_lexicon_entries(req: FunASRLabLexiconIdsRequest):
    try:
        return service.confirm_lexicon_entries(ids=req.ids)
    except FunASRLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/test/funasr-lab/lexicon/apply-incremental")
def apply_funasr_lab_incremental_lexicon(req: FunASRLabLexiconApplyRequest):
    try:
        return service.apply_incremental_lexicon(scope=req.scope, ids=req.ids)
    except FunASRLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/test/funasr-lab/lexicon/disable")
def disable_funasr_lab_lexicon_entries(req: FunASRLabLexiconDisableRequest):
    try:
        return service.disable_lexicon_entries(ids=req.ids, reason=req.reason)
    except FunASRLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/test/funasr-lab/lexicon/export-training-pack")
def export_funasr_lab_lexicon_training_pack(req: FunASRLabLexiconExportRequest):
    try:
        return service.export_lexicon_training_pack(statuses=req.statuses, ids=req.ids)
    except FunASRLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/test/funasr-lab/tracking/record")
def record_funasr_lab_tracking(req: FunASRLabTrackingRecordRequest):
    try:
        return service.record_tracking_entry(
            intake_date=req.intake_date,
            raw_name=req.raw_name,
            normalized_name=req.normalized_name,
            unit=req.unit,
            quantity=req.quantity,
            category=req.category,
            transcript=req.transcript,
            source=req.source,
        )
    except FunASRLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/test/funasr-lab/transcribe")
async def transcribe_funasr_lab_audio(
    audio: UploadFile = File(...),
    model: str = Form(default="Qwen/Qwen3-ASR-1.7B"),
    device: str = Form(default="auto"),
    language: str | None = Form(default="Chinese"),
    max_new_tokens: int = Form(default=256),
    use_domain_context: str | None = Form(default="true"),
    extra_context: str | None = Form(default=None),
    compare_with_baseline: str | None = Form(default="false"),
    parse_daily_intake: str | None = Form(default="false"),
    retain_training_audio: str | None = Form(default="false"),
    intake_date: str | None = Form(default=None),
    category: str | None = Form(default=None),
):
    try:
        config = FunASRLabConfig(
            model=(model or "Qwen/Qwen3-ASR-1.7B").strip() or "Qwen/Qwen3-ASR-1.7B",
            device=(device or "auto").strip() or "auto",
            language=(language or "").strip() or "Chinese",
            max_new_tokens=max(int(max_new_tokens or 256), 1),
            use_domain_context=_to_bool(use_domain_context, default=True),
            extra_context=(extra_context or "").strip() or None,
            compare_with_baseline=_to_bool(compare_with_baseline),
            parse_daily_intake=_to_bool(parse_daily_intake),
            retain_training_audio=_to_bool(retain_training_audio),
            intake_date=(intake_date or "").strip() or None,
            category=(category or "").strip() or None,
        )
        return service.transcribe_audio(
            config=config,
            file_bytes=await audio.read(),
            filename=audio.filename or "funasr-lab-audio.wav",
            content_type=audio.content_type,
        )
    except FunASRLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
