import asyncio
import json
import os
import re
import string
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.models.schemas import (
    BrowseRequest,
    BrowseResponse,
    DedupRequest,
    DedupResponse,
    DetectRequest,
    DetectResponse,
    TransferDetail,
    MonthlyTransferPreviewResponse,
    TransferRequest,
    TransferResponse,
    TransferTemplateStatusResponse,
    VarietiesRequest,
    VarietiesResponse,
)
from backend.api.upload_utils import (
    build_download_response,
    create_zip_archive,
    parse_json_form_value,
    save_upload,
    save_uploads,
)
from backend.services.doc_service import DocService
from backend.services.template_library_service import (
    get_transfer_template_path,
    get_transfer_templates,
    save_transfer_template,
)

import logging

_logger = logging.getLogger(__name__)

router = APIRouter()
doc_service = DocService()


def _run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, *args)


@router.post("/detect", response_model=DetectResponse)
async def detect_tables(req: DetectRequest):
    if not os.path.isdir(req.folder_path):
        raise HTTPException(status_code=400, detail="文件夹路径无效")

    y, m, d = req.date.split("-")
    pattern = re.compile(
        rf"农残检测记录表{re.escape(y)}\.{re.escape(m)}\.{re.escape(d)}(?:-(\d+))?\.docx$"
    )

    detected = []
    for filename in os.listdir(req.folder_path):
        match = pattern.match(filename)
        if match:
            num = int(match.group(1)) if match.group(1) else 0
            detected.append((num, os.path.join(req.folder_path, filename)))

    detected.sort(key=lambda x: x[0])
    files = [path for _, path in detected]
    return DetectResponse(files=files, count=len(files))


@router.post("/varieties", response_model=VarietiesResponse)
async def extract_varieties(req: VarietiesRequest):
    if not req.table_paths:
        raise HTTPException(status_code=400, detail="未提供大表文件路径")

    varieties = doc_service.extract_all_varieties(req.table_paths)
    return VarietiesResponse(varieties=varieties, count=len(varieties))


@router.post("/varieties/upload", response_model=VarietiesResponse)
async def extract_varieties_from_uploads(
    table_files: list[UploadFile] = File(...),
):
    with tempfile.TemporaryDirectory(prefix="transfer-varieties-") as tmpdir:
        saved_paths = await save_uploads(table_files, Path(tmpdir) / "tables", "table")
        varieties = await run_in_threadpool(
            doc_service.extract_all_varieties,
            [str(path) for path in saved_paths],
        )
    return VarietiesResponse(varieties=varieties, count=len(varieties))


@router.post("/dedup", response_model=DedupResponse)
async def dedup_veg_names(req: DedupRequest):
    seen = set()
    deduped = []
    for name in req.veg_names:
        key = name.strip().lower()
        if key not in seen:
            seen.add(key)
            deduped.append(name)

    removed = len(req.veg_names) - len(deduped)
    return DedupResponse(
        original=req.veg_names,
        deduplicated=deduped,
        removed_count=removed,
    )


@router.get("/templates", response_model=TransferTemplateStatusResponse)
async def get_templates():
    return TransferTemplateStatusResponse(**get_transfer_templates())


@router.post("/templates/upload", response_model=TransferTemplateStatusResponse)
async def upload_template(
    small_type: str = Form(...),
    template_file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory(prefix="transfer-template-") as tmpdir:
        saved_path = await save_upload(template_file, Path(tmpdir), "small-template")
        try:
            status = save_transfer_template(small_type, saved_path, template_file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TransferTemplateStatusResponse(**status)


@router.post("/monthly/preview", response_model=MonthlyTransferPreviewResponse)
async def preview_monthly_transfer(
    month: str = Form(...),
    table_files: list[UploadFile] = File(...),
):
    with tempfile.TemporaryDirectory(prefix="transfer-monthly-preview-") as tmpdir:
        saved_tables = await save_uploads(table_files, Path(tmpdir) / "tables", "table")
        result = doc_service.preview_monthly_groups([str(path) for path in saved_tables], month)
    return MonthlyTransferPreviewResponse(success=bool(result["groups"]), **result)


@router.post("/execute", response_model=TransferResponse)
async def execute_transfer(req: TransferRequest):
    if not req.table_paths:
        raise HTTPException(status_code=400, detail="未提供大表文件")
    if not req.small_template_path:
        raise HTTPException(status_code=400, detail="未提供小表模板")
    if not req.veg_names:
        raise HTTPException(status_code=400, detail="未提供菜名")
    if not req.output_dir:
        raise HTTPException(status_code=400, detail="未提供输出目录")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(req.output_dir, f"{req.small_type}_数据迁移_{timestamp}.docx")

    result = await _run_in_executor(
        doc_service.process_multiple_tables,
        req.table_paths,
        req.small_template_path,
        req.veg_names,
        output_path,
    )

    details = [
        TransferDetail(variety=d["variety"], rate=d["rate"], result=d["result"])
        for d in result.get("details", [])
    ]

    return TransferResponse(
        success=True,
        processed_files=result["processed_files"],
        matched_count=result["matched_count"],
        written_count=result["written_count"],
        output_file=result.get("output_file"),
        message=result["message"],
        details=details,
    )


@router.post("/execute/upload")
async def execute_transfer_upload(
    veg_names_json: str = Form(...),
    small_type: str = Form(default="small"),
    table_files: list[UploadFile] = File(...),
    small_template: UploadFile = File(...),
):
    veg_names = parse_json_form_value(
        veg_names_json,
        field_name="veg_names_json",
        expected_type=list,
    )
    normalized_veg_names = [
        str(item).strip()
        for item in veg_names
        if str(item).strip()
    ]
    if not normalized_veg_names:
        raise HTTPException(status_code=400, detail="未提供菜名")

    with tempfile.TemporaryDirectory(prefix="transfer-execute-") as tmpdir:
        root = Path(tmpdir)
        saved_tables = await save_uploads(table_files, root / "tables", "table")
        template_path = await save_upload(small_template, root / "template", "small-template")
        output_name = f"{small_type}_数据迁移_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        output_path = root / "output" / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = await run_in_threadpool(
            doc_service.process_multiple_tables,
            [str(path) for path in saved_tables],
            str(template_path),
            normalized_veg_names,
            str(output_path),
        )

        generated_path = Path(result.get("output_file") or output_path)
        if not generated_path.exists():
            raise HTTPException(status_code=500, detail="数据迁移任务已结束，但没有生成输出文件")

        return build_download_response(
            generated_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            extra_headers={
                "X-Operation-Message": result.get("message", "数据迁移已完成"),
                "X-Processed-Files": str(result.get("processed_files", 0)),
                "X-Matched-Count": str(result.get("matched_count", 0)),
                "X-Written-Count": str(result.get("written_count", 0)),
            },
        )


@router.post("/monthly/execute")
async def execute_monthly_transfer_upload(
    month: str = Form(...),
    veg_names_json: str = Form(...),
    small_type: str = Form(default="滨鲜"),
    use_saved_template: str = Form(default="true"),
    table_files: list[UploadFile] = File(...),
    small_template: UploadFile | None = File(default=None),
):
    veg_names = parse_json_form_value(
        veg_names_json,
        field_name="veg_names_json",
        expected_type=list,
    )
    normalized_veg_names = [
        str(item).strip()
        for item in veg_names
        if str(item).strip()
    ]
    if not normalized_veg_names:
        raise HTTPException(status_code=400, detail="未提供菜名")

    with tempfile.TemporaryDirectory(prefix="transfer-monthly-") as tmpdir:
        root = Path(tmpdir)
        saved_tables = await save_uploads(table_files, root / "tables", "table")
        try:
            if small_template is not None and small_template.filename:
                template_path = await save_upload(small_template, root / "template", "small-template")
            else:
                template_path = get_transfer_template_path(small_type)
        except FileNotFoundError as exc:
            if use_saved_template.lower() == "false":
                raise HTTPException(status_code=400, detail="请上传本次使用的小表模板") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        preview = doc_service.preview_monthly_groups([str(path) for path in saved_tables], month)
        if not preview["groups"]:
            raise HTTPException(status_code=400, detail="未识别到所选月份的大表文件")

        output_dir = root / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "month": month,
            "success": [],
            "skipped": [],
            "unrecognized_files": preview["unrecognized_files"],
            "generated_files": [],
        }

        for group in preview["groups"]:
            date_text = group["date"]
            output_name = f"{small_type}_数据迁移_{date_text.replace('-', '.')}.docx"
            output_path = output_dir / output_name
            result = await run_in_threadpool(
                doc_service.process_multiple_tables,
                group["files"],
                str(template_path),
                normalized_veg_names,
                str(output_path),
            )
            generated_path = Path(result.get("output_file") or output_path)
            if generated_path.exists():
                manifest["success"].append({
                    "date": date_text,
                    "input_files": [Path(path).name for path in group["files"]],
                    "matched_count": result.get("matched_count", 0),
                    "written_count": result.get("written_count", 0),
                    "output_file": generated_path.name,
                })
                manifest["generated_files"].append(generated_path.name)
            else:
                manifest["skipped"].append({
                    "date": date_text,
                    "input_files": [Path(path).name for path in group["files"]],
                    "reason": result.get("message", "未生成输出文件"),
                })

        manifest["success_count"] = len(manifest["success"])
        manifest["skipped_count"] = len(manifest["skipped"]) + len(manifest["unrecognized_files"])
        manifest["message"] = (
            f"月度数据迁移完成，成功 {manifest['success_count']} 天，"
            f"跳过 {manifest['skipped_count']} 项"
        )
        (output_dir / "处理结果清单.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        generated_files = sorted(path for path in output_dir.iterdir() if path.is_file())
        generated_docx = [path for path in generated_files if path.suffix.lower() == ".docx"]
        if not generated_docx:
            detail = manifest["skipped"][0]["reason"] if manifest["skipped"] else "没有生成任何月度数据迁移文件"
            raise HTTPException(status_code=400, detail=detail)

        archive_path = create_zip_archive(root / f"数据迁移月度结果-{month}.zip", generated_files, arc_root=output_dir)
        return build_download_response(
            archive_path,
            media_type="application/zip",
            extra_headers={
                "X-Operation-Message": manifest["message"],
                "X-Processed-Files": str(sum(group["count"] for group in preview["groups"])),
                "X-Matched-Count": str(sum(item["matched_count"] for item in manifest["success"])),
                "X-Written-Count": str(sum(item["written_count"] for item in manifest["success"])),
                "X-Generated-Count": str(len(generated_docx)),
                "X-Skipped-Count": str(manifest["skipped_count"]),
            },
        )


@router.post("/find-files", response_model=BrowseResponse)
async def find_docx_files(req: BrowseRequest):
    """List .doc/.docx files in a server-side directory."""
    dir_path = (req.path or "").strip()
    if not dir_path or not os.path.isdir(dir_path):
        raise HTTPException(status_code=400, detail="目录路径无效")
    entries = os.listdir(dir_path)
    docx_files = sorted(
        e for e in entries
        if os.path.isfile(os.path.join(dir_path, e)) and e.lower().endswith((".doc", ".docx"))
    )
    return BrowseResponse(path=dir_path, subdirs=[], files=docx_files)


@router.post("/execute-from-paths")
async def execute_transfer_from_paths(
    table_paths_json: str = Form(...),
    small_template_path: str = Form(...),
    veg_names_json: str = Form(...),
    small_type: str = Form(default="small"),
    output_dir: str = Form(default=""),
):
    """Single transfer execution using server-side file paths.

    When ``output_dir`` is provided the output file is written directly to
    that directory and a JSON response is returned (no download).  Otherwise
    the legacy tempdir-and-download behaviour is preserved.
    """
    table_paths = parse_json_form_value(
        table_paths_json,
        field_name="table_paths_json",
        expected_type=list,
    )
    normalized_table_paths = [str(p).strip() for p in table_paths if str(p).strip()]
    if not normalized_table_paths:
        raise HTTPException(status_code=400, detail="未提供大表文件路径")

    veg_names = parse_json_form_value(
        veg_names_json,
        field_name="veg_names_json",
        expected_type=list,
    )
    normalized_veg_names = [
        str(item).strip()
        for item in veg_names
        if str(item).strip()
    ]
    if not normalized_veg_names:
        raise HTTPException(status_code=400, detail="未提供菜名")

    template_path = small_template_path.strip()
    if not os.path.exists(template_path):
        raise HTTPException(status_code=400, detail="小表模板路径无效")

    for p in normalized_table_paths:
        if not os.path.exists(p):
            raise HTTPException(status_code=400, detail=f"大表文件不存在: {p}")

    if output_dir.strip():
        target_dir = Path(output_dir.strip())
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="输出目录不存在")
        output_name = f"{small_type}_数据迁移_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        output_path = target_dir / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = await run_in_threadpool(
            doc_service.process_multiple_tables,
            normalized_table_paths,
            template_path,
            normalized_veg_names,
            str(output_path),
        )

        generated_path = Path(result.get("output_file") or output_path)
        if not generated_path.exists():
            raise HTTPException(status_code=500, detail="数据迁移任务已结束，但没有生成输出文件")

        return {
            "success": True,
            "message": result.get("message", "数据迁移已完成"),
            "processed_files": result.get("processed_files", len(normalized_table_paths)),
            "matched_count": result.get("matched_count", 0),
            "written_count": result.get("written_count", 0),
            "output_file": str(generated_path),
        }

    # Legacy tempdir + download path
    with tempfile.TemporaryDirectory(prefix="transfer-execute-") as tmpdir:
        root = Path(tmpdir)
        output_name = f"{small_type}_数据迁移_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        output_path = root / "output" / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = await run_in_threadpool(
            doc_service.process_multiple_tables,
            normalized_table_paths,
            template_path,
            normalized_veg_names,
            str(output_path),
        )

        generated_path = Path(result.get("output_file") or output_path)
        if not generated_path.exists():
            raise HTTPException(status_code=500, detail="数据迁移任务已结束，但没有生成输出文件")

        return build_download_response(
            generated_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            extra_headers={
                "X-Operation-Message": result.get("message", "数据迁移已完成"),
                "X-Processed-Files": str(result.get("processed_files", 0)),
                "X-Matched-Count": str(result.get("matched_count", 0)),
                "X-Written-Count": str(result.get("written_count", 0)),
            },
        )


@router.post("/log-restore")
async def log_path_restore(req: BrowseRequest):
    """Log when the frontend restores path-lock state from localStorage cache."""
    dir_path = (req.path or "").strip()
    _logger.info("数据迁移路径锁定状态已从缓存恢复，目录: %s", dir_path or "(空)")
    return {"ok": True}


@router.post("/browse", response_model=BrowseResponse)
async def browse_directory(req: BrowseRequest):
    path = (req.path or "").strip()

    if not path:
        if os.name == "nt":
            drives = [
                f"{letter}:\\"
                for letter in string.ascii_uppercase
                if os.path.exists(f"{letter}:\\")
            ]
            return BrowseResponse(path="", subdirs=drives, files=[])
        return BrowseResponse(path=os.path.sep, subdirs=[os.path.sep], files=[])

    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="路径无效")

    entries = os.listdir(path)
    subdirs = sorted([e for e in entries if os.path.isdir(os.path.join(path, e))])
    files = sorted([e for e in entries if os.path.isfile(os.path.join(path, e))])
    return BrowseResponse(path=path, subdirs=subdirs, files=files)
