from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from backend.auth.dependencies import require_permission
from backend.models.schemas import (
    DailyIntakeDeleteResponse,
    DailyIntakeHistoryResponse,
    DailyIntakeItemMutationResponse,
    DailyIntakeItemUpdateRequest,
    DailyIntakeItemUpsertRequest,
    DailyIntakeParseRequest,
    DailyIntakeParseResponse,
    DailyIntakeSheetResponse,
    DailyIntakeSpeechCapabilitiesResponse,
    DailyIntakeSpeechDiagnosticsResponse,
)
from backend.diagnostics.asr_self_check import run_asr_self_check
from backend.services.daily_intake_asr_service import DailyIntakeAsrError, DailyIntakeAsrService
from backend.services.daily_intake_service import DailyIntakeService

router = APIRouter()
service = DailyIntakeService()
speech_to_text_service = DailyIntakeAsrService(daily_intake_service=service)


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, KeyError):
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/today", response_model=DailyIntakeSheetResponse, dependencies=[Depends(require_permission("daily_check:view"))])
def get_today_daily_intake_sheet():
    return DailyIntakeSheetResponse(**service.get_today_sheet())


@router.get("/history", response_model=DailyIntakeHistoryResponse, dependencies=[Depends(require_permission("daily_check:view"))])
def list_daily_intake_history(limit: int = Query(default=30, ge=1, le=365)):
    return DailyIntakeHistoryResponse(**service.list_history(limit=limit))


@router.get(
    "/speech-capabilities",
    response_model=DailyIntakeSpeechCapabilitiesResponse,
    dependencies=[Depends(require_permission("daily_check:view"))],
)
def get_daily_intake_speech_capabilities():
    return DailyIntakeSpeechCapabilitiesResponse(**speech_to_text_service.capabilities())


@router.get(
    "/asr-self-check",
    dependencies=[Depends(require_permission("daily_check:view"))],
)
def get_daily_intake_asr_self_check():
    """Dump loaded ASR module locations for diagnosing stub fallbacks."""
    return run_asr_self_check(strict=False)


@router.get(
    "/speech-runtime-diagnostics",
    response_model=DailyIntakeSpeechDiagnosticsResponse,
    dependencies=[Depends(require_permission("daily_check:view"))],
)
def get_daily_intake_speech_runtime_diagnostics(
    probe_runtime: bool = Query(default=True),
):
    return DailyIntakeSpeechDiagnosticsResponse(
        **speech_to_text_service.diagnostics(probe_runtime=probe_runtime)
    )


@router.get("/asr-shadow-compare", dependencies=[Depends(require_permission("daily_check:view"))])
def list_daily_intake_asr_shadow_compare(limit: int = Query(default=50, ge=1, le=500)):
    records = speech_to_text_service.shadow_store.read_recent(limit=limit)
    return {
        "success": True,
        "path": str(speech_to_text_service.shadow_store.path),
        "total_returned": len(records),
        "records": records,
    }


@router.get("/asr-shadow-compare/export", dependencies=[Depends(require_permission("daily_check:export"))])
def export_daily_intake_asr_shadow_compare():
    path = speech_to_text_service.shadow_store.export_path()
    return FileResponse(
        path,
        media_type="application/x-ndjson",
        filename=path.name,
    )


@router.get("/{intake_date}", response_model=DailyIntakeSheetResponse, dependencies=[Depends(require_permission("daily_check:view"))])
def get_daily_intake_sheet(intake_date: str):
    try:
        return DailyIntakeSheetResponse(**service.get_sheet(intake_date))
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.post("/items", response_model=DailyIntakeItemMutationResponse, dependencies=[Depends(require_permission("daily_check:create"))])
def create_daily_intake_item(req: DailyIntakeItemUpsertRequest):
    try:
        result = service.add_item(
            intake_date=req.intake_date,
            name=req.name,
            category=req.category,
            quantity=req.quantity,
            unit=req.unit,
            source=req.source,
            transcript=req.transcript,
        )
        return DailyIntakeItemMutationResponse(**result)
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.put(
    "/items/{item_id}",
    response_model=DailyIntakeItemMutationResponse,
    dependencies=[Depends(require_permission("daily_check:update"))],
)
def update_daily_intake_item(item_id: int, req: DailyIntakeItemUpdateRequest):
    try:
        result = service.update_item(
            item_id,
            name=req.name,
            category=req.category,
            quantity=req.quantity,
            unit=req.unit,
            source=req.source,
            transcript=req.transcript,
        )
        return DailyIntakeItemMutationResponse(**result)
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.delete(
    "/items/{item_id}",
    response_model=DailyIntakeDeleteResponse,
    dependencies=[Depends(require_permission("daily_check:delete"))],
)
def delete_daily_intake_item(item_id: int):
    try:
        return DailyIntakeDeleteResponse(**service.delete_item(item_id))
    except (ValueError, KeyError) as exc:
        _raise_http_error(exc)


@router.post(
    "/parse-transcript",
    response_model=DailyIntakeParseResponse,
    dependencies=[Depends(require_permission("daily_check:create"))],
)
def parse_daily_intake_transcript(req: DailyIntakeParseRequest):
    try:
        return DailyIntakeParseResponse(
            **service.parse_transcript(
                transcript=req.transcript,
                intake_date=req.intake_date,
                category=req.category,
            )
        )
    except ValueError as exc:
        _raise_http_error(exc)


@router.post(
    "/transcribe-audio",
    response_model=DailyIntakeParseResponse,
    dependencies=[Depends(require_permission("daily_check:create"))],
)
async def transcribe_daily_intake_audio(
    intake_date: str = Form(...),
    category: str | None = Form(default=None),
    asr_provider: str | None = Form(default="auto"),
    fallback_enabled: str | None = Form(default=None),
    audio: UploadFile = File(...),
):
    try:
        payload = await run_in_threadpool(
            speech_to_text_service.transcribe_audio,
            file_bytes=await audio.read(),
            filename=audio.filename or "daily-intake-recording.webm",
            content_type=audio.content_type,
            intake_date=intake_date,
            category=category,
            asr_provider=asr_provider,
            fallback_enabled=_parse_optional_bool(fallback_enabled),
        )
        return DailyIntakeParseResponse(**payload)
    except DailyIntakeAsrError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        _raise_http_error(exc)


def _parse_optional_bool(raw_value: str | None) -> bool | None:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip().lower()
    if not normalized:
        return None
    return normalized not in {"0", "false", "no"}
