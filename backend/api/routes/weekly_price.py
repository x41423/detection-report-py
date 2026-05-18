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
    WeeklyQuoteDeleteRequest,
    WeeklyQuoteEntryInput,
    WeeklyQuoteExportRequest,
    WeeklyQuoteExportResponse,
    WeeklyQuoteImportRequest,
    WeeklyQuoteImportResponse,
    WeeklyQuoteMeasureUnitCreateRequest,
    WeeklyQuoteMeasureUnitCreateResponse,
    WeeklyQuotePreviewRequest,
    WeeklyQuotePreviewResponse,
    WeeklyQuoteSaveRequest,
    WeeklyQuoteSupplierCreateRequest,
    WeeklyQuoteSupplierCreateResponse,
    WeeklyQuoteSummaryOptionsResponse,
    WeeklyQuoteWeekOverviewResponse,
    WeeklyQuoteWeekSummaryRequest,
    WeeklyQuoteWeekSummaryResponse,
)
from backend.services.weekly_price_service import WeeklyPriceService
from backend.services.weekly_quote_summary_service import WeeklyQuoteSummaryService

router = APIRouter()
service = WeeklyPriceService()
summary_service = WeeklyQuoteSummaryService()


def _build_weekly_price_upload_output_name(update_file_name: str | None) -> str:
    stem = Path(str(update_file_name or "")).stem or "weekly-price"
    return f"{stem}_weekly_updated.xlsx"


def _raise_bad_request(exc: Exception) -> None:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.get(
    "/summary/options",
    response_model=WeeklyQuoteSummaryOptionsResponse,
    dependencies=[Depends(require_permission("weekly_quote:view"))],
)
def get_weekly_quote_summary_options():
    result = summary_service.get_options()
    return WeeklyQuoteSummaryOptionsResponse(**result)


@router.post(
    "/summary/suppliers",
    response_model=WeeklyQuoteSupplierCreateResponse,
    dependencies=[Depends(require_permission("weekly_quote:create"))],
)
def create_weekly_quote_supplier(req: WeeklyQuoteSupplierCreateRequest):
    try:
        result = summary_service.create_supplier(
            name=req.name,
            weekly_batch_limit=req.weekly_batch_limit,
            summary_rule=req.summary_rule,
        )
    except ValueError as exc:
        _raise_bad_request(exc)
    return WeeklyQuoteSupplierCreateResponse(**result)


@router.post(
    "/summary/measure-units",
    response_model=WeeklyQuoteMeasureUnitCreateResponse,
    dependencies=[Depends(require_permission("weekly_quote:create"))],
)
def create_weekly_quote_measure_unit(req: WeeklyQuoteMeasureUnitCreateRequest):
    try:
        result = summary_service.create_measure_unit(req.name)
    except ValueError as exc:
        _raise_bad_request(exc)
    return WeeklyQuoteMeasureUnitCreateResponse(**result)


@router.post(
    "/summary/import",
    response_model=WeeklyQuoteImportResponse,
    dependencies=[Depends(require_permission("weekly_quote:create"))],
)
def import_weekly_quote_summary(req: WeeklyQuoteImportRequest):
    try:
        result = summary_service.import_batch(
            supplier=req.supplier,
            quote_date=req.quote_date,
            source_path=req.source_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        _raise_bad_request(exc)
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
        try:
            result = await run_in_threadpool(
                summary_service.import_batch,
                supplier,
                quote_date,
                str(source_path),
            )
        except (FileNotFoundError, ValueError) as exc:
            _raise_bad_request(exc)
    return WeeklyQuoteImportResponse(**result)


@router.post(
    "/summary/preview",
    response_model=WeeklyQuotePreviewResponse,
    dependencies=[Depends(require_permission("weekly_quote:view"))],
)
def preview_weekly_quote_summary_data(req: WeeklyQuotePreviewRequest):
    try:
        result = summary_service.preview(
            batches=[batch.model_dump() for batch in req.batches],
        )
    except ValueError as exc:
        _raise_bad_request(exc)
    return WeeklyQuotePreviewResponse(**result)


@router.post(
    "/summary/export",
    response_model=WeeklyQuoteExportResponse,
    dependencies=[Depends(require_permission("weekly_quote:export"))],
)
def export_weekly_quote_summary_data(req: WeeklyQuoteExportRequest):
    try:
        result = summary_service.export(
            workbook_path=req.workbook_path,
            batches=[batch.model_dump() for batch in req.batches],
        )
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        _raise_bad_request(exc)
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
        try:
            result = await run_in_threadpool(
                summary_service.export,
                str(workbook_path),
                batches,
            )
        except (FileNotFoundError, PermissionError, ValueError) as exc:
            _raise_bad_request(exc)

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


@router.post("/summary/export/week/upload", dependencies=[Depends(require_permission("weekly_quote:export"))])
async def export_weekly_quote_summary_week_upload(
    date: str = Form(...),
    workbook_file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory(prefix="weekly-quote-week-export-") as tmpdir:
        root = Path(tmpdir)
        workbook_path = await save_upload(workbook_file, root / "inputs", "summary-template")
        try:
            result = await run_in_threadpool(
                summary_service.export_week,
                str(workbook_path),
                date,
            )
        except (FileNotFoundError, PermissionError, ValueError) as exc:
            _raise_bad_request(exc)

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


@router.post("/summary/save", dependencies=[Depends(require_permission("weekly_quote:create"))])
def save_quote_batch(req: WeeklyQuoteSaveRequest):
    svc = WeeklyQuoteSummaryService()
    try:
        return svc.save_manual_batch(
            req.supplier, req.quote_date,
            [e.model_dump() for e in req.entries],
            req.source_label,
        )
    except ValueError as exc:
        _raise_bad_request(exc)


@router.get("/summary/batches", dependencies=[Depends(require_permission("weekly_quote:view"))])
def list_quote_batches(supplier: str):
    svc = WeeklyQuoteSummaryService()
    return svc.list_saved_batches(supplier)


@router.post("/summary/delete", dependencies=[Depends(require_permission("weekly_quote:delete"))])
def delete_quote_batch(req: WeeklyQuoteDeleteRequest):
    svc = WeeklyQuoteSummaryService()
    return svc.delete_batch(req.supplier, req.quote_date)


@router.get(
    "/summary/week",
    response_model=WeeklyQuoteWeekOverviewResponse,
    dependencies=[Depends(require_permission("weekly_quote:view"))],
)
def weekly_quote_week_overview(date: str):
    svc = WeeklyQuoteSummaryService()
    try:
        return svc.get_week_overview(date)
    except ValueError as exc:
        _raise_bad_request(exc)


@router.post(
    "/summary/weekly",
    response_model=WeeklyQuoteWeekSummaryResponse,
    dependencies=[Depends(require_permission("weekly_quote:view"))],
)
def weekly_quote_summary(req: WeeklyQuoteWeekSummaryRequest):
    svc = WeeklyQuoteSummaryService()
    try:
        return svc.get_weekly_summary(req.supplier, req.date)
    except ValueError as exc:
        _raise_bad_request(exc)


@router.get("/summary/suppliers", dependencies=[Depends(require_permission("weekly_quote:view"))])
def list_quote_suppliers():
    svc = WeeklyQuoteSummaryService()
    return svc.get_all_suppliers()
