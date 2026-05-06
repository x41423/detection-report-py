import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi import File, Form, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.auth.dependencies import require_permission
from backend.api.upload_utils import (
    build_download_response,
    parse_json_form_value,
    save_upload,
)
from backend.models.schemas import (
    WeeklyPriceAliasDeleteRequest,
    WeeklyPriceAliasListResponse,
    WeeklyPriceAliasUpsertRequest,
    WeeklyPriceExecuteRequest,
    WeeklyPriceExecuteResponse,
    WeeklyPricePreviewRequest,
    WeeklyPricePreviewResponse,
    WeeklyQuoteExportRequest,
    WeeklyQuoteExportResponse,
    WeeklyQuoteImportRequest,
    WeeklyQuoteImportResponse,
    WeeklyQuotePreviewRequest,
    WeeklyQuotePreviewResponse,
)
from backend.services.weekly_price_service import WeeklyPriceService
from backend.services.weekly_quote_summary_service import WeeklyQuoteSummaryService

router = APIRouter()
service = WeeklyPriceService()
summary_service = WeeklyQuoteSummaryService()


def _build_weekly_price_upload_output_name(update_file_name: str | None) -> str:
    stem = Path(str(update_file_name or "")).stem or "weekly-price"
    return f"{stem}_weekly_updated.xlsx"


@router.post("/preview", response_model=WeeklyPricePreviewResponse, dependencies=[Depends(require_permission("weekly_quote:view"))])
def preview_weekly_price(req: WeeklyPricePreviewRequest):
    try:
        result = service.preview(
            update_path=req.update_path,
            reference_path=req.reference_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WeeklyPricePreviewResponse(**result)


@router.post(
    "/preview/upload",
    response_model=WeeklyPricePreviewResponse,
    dependencies=[Depends(require_permission("weekly_quote:view"))],
)
async def preview_weekly_price_upload(
    update_file: UploadFile = File(...),
    reference_file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory(prefix="weekly-price-preview-") as tmpdir:
        root = Path(tmpdir)
        update_path = await save_upload(update_file, root / "inputs", "update")
        reference_path = await save_upload(reference_file, root / "inputs", "reference")
        try:
            result = await run_in_threadpool(
                service.preview,
                str(update_path),
                str(reference_path),
            )
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WeeklyPricePreviewResponse(**result)


@router.post("/execute", response_model=WeeklyPriceExecuteResponse, dependencies=[Depends(require_permission("weekly_quote:update"))])
def execute_weekly_price(req: WeeklyPriceExecuteRequest):
    try:
        result = service.execute(
            update_path=req.update_path,
            reference_path=req.reference_path,
            output_path=req.output_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return WeeklyPriceExecuteResponse(**result)


@router.post("/execute/upload", dependencies=[Depends(require_permission("weekly_quote:update"))])
async def execute_weekly_price_upload(
    update_file: UploadFile = File(...),
    reference_file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory(prefix="weekly-price-execute-") as tmpdir:
        root = Path(tmpdir)
        update_path = await save_upload(update_file, root / "inputs", "update")
        reference_path = await save_upload(reference_file, root / "inputs", "reference")
        output_path = root / "output" / _build_weekly_price_upload_output_name(update_file.filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = await run_in_threadpool(
                service.execute,
                str(update_path),
                str(reference_path),
                str(output_path),
            )
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        generated_path = Path(result["output_path"])
        if not generated_path.exists():
            raise HTTPException(status_code=500, detail="周报价更新已结束，但没有生成输出文件")

        return build_download_response(
            generated_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            extra_headers={
                "X-Operation-Message": result.get("message", "周报价更新已完成"),
                "X-Matched-Count": str(result.get("matched_count", 0)),
                "X-Updated-Count": str(result.get("updated_count", 0)),
            },
        )


@router.get("/aliases", response_model=WeeklyPriceAliasListResponse, dependencies=[Depends(require_permission("weekly_quote:aliases"))])
def list_weekly_price_aliases():
    result = service.list_aliases()
    return WeeklyPriceAliasListResponse(**result)


@router.put("/aliases", response_model=WeeklyPriceAliasListResponse, dependencies=[Depends(require_permission("weekly_quote:aliases"))])
def upsert_weekly_price_aliases(req: WeeklyPriceAliasUpsertRequest):
    result = service.upsert_aliases(req.mappings)
    return WeeklyPriceAliasListResponse(**result)


@router.delete("/aliases", response_model=WeeklyPriceAliasListResponse, dependencies=[Depends(require_permission("weekly_quote:aliases"))])
def delete_weekly_price_alias(req: WeeklyPriceAliasDeleteRequest):
    result = service.delete_alias(req.source_name)
    return WeeklyPriceAliasListResponse(**result)


@router.post(
    "/summary/import",
    response_model=WeeklyQuoteImportResponse,
    dependencies=[Depends(require_permission("weekly_quote:create"))],
)
def import_weekly_quote_summary(req: WeeklyQuoteImportRequest):
    result = summary_service.import_batch(
        supplier=req.supplier,
        quote_date=req.quote_date,
        source_path=req.source_path,
    )
    return WeeklyQuoteImportResponse(**result)


@router.post(
    "/summary/import/upload",
    response_model=WeeklyQuoteImportResponse,
    dependencies=[Depends(require_permission("weekly_quote:create"))],
)
async def import_weekly_quote_summary_upload(
    supplier: str = Form(...),
    quote_date: str = Form(...),
    source_file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory(prefix="weekly-quote-import-") as tmpdir:
        source_path = await save_upload(source_file, Path(tmpdir) / "inputs", "summary-import")
        result = await run_in_threadpool(
            summary_service.import_batch,
            supplier,
            quote_date,
            str(source_path),
        )
    return WeeklyQuoteImportResponse(**result)


@router.post(
    "/summary/preview",
    response_model=WeeklyQuotePreviewResponse,
    dependencies=[Depends(require_permission("weekly_quote:view"))],
)
def preview_weekly_quote_summary_data(req: WeeklyQuotePreviewRequest):
    result = summary_service.preview(
        batches=[batch.model_dump() for batch in req.batches],
    )
    return WeeklyQuotePreviewResponse(**result)


@router.post(
    "/summary/export",
    response_model=WeeklyQuoteExportResponse,
    dependencies=[Depends(require_permission("weekly_quote:export"))],
)
def export_weekly_quote_summary_data(req: WeeklyQuoteExportRequest):
    result = summary_service.export(
        workbook_path=req.workbook_path,
        batches=[batch.model_dump() for batch in req.batches],
    )
    return WeeklyQuoteExportResponse(**result)


@router.post("/summary/export/upload", dependencies=[Depends(require_permission("weekly_quote:export"))])
async def export_weekly_quote_summary_data_upload(
    batches_json: str = Form(...),
    workbook_file: UploadFile = File(...),
):
    batches = parse_json_form_value(
        batches_json,
        field_name="batches_json",
        expected_type=list,
    )
    with tempfile.TemporaryDirectory(prefix="weekly-quote-export-") as tmpdir:
        root = Path(tmpdir)
        workbook_path = await save_upload(workbook_file, root / "inputs", "summary-template")
        result = await run_in_threadpool(
            summary_service.export,
            str(workbook_path),
            batches,
        )

        generated_path = Path(result["workbook_path"])
        if not generated_path.exists():
            raise HTTPException(status_code=500, detail="周报价汇总导出已结束，但没有生成输出文件")

        media_type = (
            "application/vnd.ms-excel.sheet.macroEnabled.12"
            if generated_path.suffix.lower() == ".xlsm"
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return build_download_response(
            generated_path,
            media_type=media_type,
            extra_headers={"X-Operation-Message": result.get("message", "周报价汇总导出已完成")},
        )
