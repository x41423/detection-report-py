"""Inspection report routes — archive management."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from backend.api.response_utils import list_response, mutation_response
from backend.api.upload_utils import save_upload
from backend.auth.dependencies import get_current_auth_context, require_permission
from backend.models.inspection_report_schemas import (
    InspectionReportCreate,
    InspectionReportUpdate,
)
from backend.services.inspection_report_service import InspectionReportService

router = APIRouter()
service = InspectionReportService()

ROOT_DIR = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT_DIR / "data" / "uploads" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ⚠️ Pitfall #8: static paths BEFORE wildcard /{id}
# ── File upload ──────────────────────────────────────────────────────

@router.post(
    "/upload",
    dependencies=[Depends(require_permission("inspection_report:create"))],
)
async def upload_report_file(file: UploadFile = File(...)):
    """Upload inspection report file (PDF/DOCX/image)."""
    allowed = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".zip"}
    ext = Path(file.filename or "report.pdf").suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    saved = await save_upload(file, REPORTS_DIR, fallback_stem="report")
    return {"success": True, "message": "文件上传成功", "url": f"/uploads/reports/{saved.name}"}


# ── List ─────────────────────────────────────────────────────────────

@router.get(
    "/",
    dependencies=[Depends(require_permission("inspection_report:view"))],
)
def list_reports(
    search: str = Query(default="", description="搜索报告名/编号/送检机构/检测机构"),
    status: str = Query(default="", description="draft | approved | rejected"),
    supplier_id: int = Query(default=0, ge=0),
    test_date_from: str = Query(default=""),
    test_date_to: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return service.list_reports(
        search=search,
        status=status,
        supplier_id=supplier_id,
        test_date_from=test_date_from,
        test_date_to=test_date_to,
        limit=limit,
        offset=offset,
    )


# ── Detail ───────────────────────────────────────────────────────────

@router.get(
    "/{report_id}",
    dependencies=[Depends(require_permission("inspection_report:view"))],
)
def get_report(report_id: int):
    result = service.get_report(report_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


# ── Create ───────────────────────────────────────────────────────────

@router.post(
    "/",
    dependencies=[Depends(require_permission("inspection_report:create"))],
)
def create_report(
    body: InspectionReportCreate,
    context=Depends(get_current_auth_context),
):
    result = service.create(body.model_dump(), context.user_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ── Update ───────────────────────────────────────────────────────────

@router.put(
    "/{report_id}",
    dependencies=[Depends(require_permission("inspection_report:update"))],
)
def update_report(report_id: int, body: InspectionReportUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    result = service.update(report_id, data)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


# ── Delete ───────────────────────────────────────────────────────────

@router.delete(
    "/{report_id}",
    dependencies=[Depends(require_permission("inspection_report:delete"))],
)
def delete_report(report_id: int):
    result = service.delete_report(report_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result
