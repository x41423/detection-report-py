import asyncio
import json
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from backend.models.schemas import (
    GenerateRatesRequest, GenerateRatesResponse, GenerateRatesItem,
    DedupJsonRequest, DedupJsonResponse,
    FormatJsonRequest, FormatJsonResponse,
    FindFilesRequest, FindFilesResponse,
    ExecuteTaskRequest, ExecuteTaskResponse,
    MonthlyListParseResponse,
    PesticideTemplateStatusResponse,
)
from backend.api.upload_utils import (
    build_download_response,
    create_zip_archive,
    parse_json_form_value,
    save_upload,
)
from backend.auth.dependencies import require_permission
from backend.services.monthly_list_parser import MonthlyListParser
from backend.services.pesticide_service import PesticideService
from backend.services.template_library_service import (
    get_pesticide_template_path,
    get_pesticide_template_versions,
    get_pesticide_templates,
    rollback_pesticide_template,
    delete_pesticide_template_version,
    save_pesticide_template,
)

router = APIRouter()
service = PesticideService()
monthly_parser = MonthlyListParser()


def _run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, *args)


@router.post("/generate-rates", response_model=GenerateRatesResponse)
async def generate_rates(req: GenerateRatesRequest):
    data = service.generate_rates(req.veg_text)
    items = [GenerateRatesItem(variety=d["variety"], rate=d["rate"]) for d in data]
    return GenerateRatesResponse(data=items, count=len(items))


@router.post("/dedup-json", response_model=DedupJsonResponse)
async def dedup_json(req: DedupJsonRequest):
    data, removed = service.dedup_json(req.json_text)
    items = [GenerateRatesItem(variety=d["variety"], rate=d["rate"]) for d in data]
    return DedupJsonResponse(data=items, removed_count=removed)


@router.post("/format-json", response_model=FormatJsonResponse)
async def format_json(req: FormatJsonRequest):
    formatted = service.format_json(req.json_text)
    return FormatJsonResponse(json_text=formatted)


@router.get("/templates", response_model=PesticideTemplateStatusResponse)
async def get_templates():
    return PesticideTemplateStatusResponse(**get_pesticide_templates())


@router.post("/templates/{kind}", response_model=PesticideTemplateStatusResponse)
async def upload_template(kind: str, template_file: UploadFile = File(...)):
    if kind not in {"big", "small"}:
        raise HTTPException(status_code=400, detail="模板类型只能是 big 或 small")
    with tempfile.TemporaryDirectory(prefix="pesticide-template-") as tmpdir:
        saved_path = await save_upload(template_file, Path(tmpdir), f"{kind}-template")
        try:
            status = save_pesticide_template(kind, saved_path, template_file.filename)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PesticideTemplateStatusResponse(**status)


@router.post("/monthly-list/parse", response_model=MonthlyListParseResponse)
async def parse_monthly_list(
    month: str = Form(default=""),
    list_text: str = Form(default=""),
    list_file: UploadFile | None = File(default=None),
):
    try:
        if list_file is not None and list_file.filename:
            with tempfile.TemporaryDirectory(prefix="pesticide-list-") as tmpdir:
                saved_path = await save_upload(list_file, Path(tmpdir), "monthly-list")
                result = monthly_parser.parse_file(saved_path, month)
        else:
            result = monthly_parser.parse_text(list_text, month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MonthlyListParseResponse(**result)


@router.post("/find-files", response_model=FindFilesResponse)
async def find_files(req: FindFilesRequest):
    result = service.find_target_files(req.big_dir, req.small_dir, req.year, req.month, req.day)
    return FindFilesResponse(**result)


@router.post("/execute", response_model=ExecuteTaskResponse)
async def execute_task(req: ExecuteTaskRequest):
    result = await _run_in_executor(
        service.execute_task,
        req.big_path, req.small_path, req.json_text,
        req.date_label, req.output_dir, req.inspector_name,
    )
    return ExecuteTaskResponse(**result)


@router.post("/execute/upload")
async def execute_task_upload(
    json_text: str = Form(...),
    date_label: str = Form(...),
    inspector_name: str = Form(default=""),
    big_file: UploadFile = File(...),
    small_file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory(prefix="pesticide-execute-") as tmpdir:
        root = Path(tmpdir)
        input_dir = root / "inputs"
        output_dir = root / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        big_path = await save_upload(big_file, input_dir, "big-table")
        small_path = await save_upload(small_file, input_dir, "small-table")

        result = await run_in_threadpool(
            service.execute_task,
            str(big_path),
            str(small_path),
            json_text,
            date_label,
            str(output_dir),
            inspector_name,
        )

        generated_files = sorted(path for path in output_dir.iterdir() if path.is_file())
        if not generated_files:
            raise HTTPException(status_code=500, detail="农残检测任务已结束，但没有生成输出文件")

        archive_name = f"pesticide-report-{Path(big_path).stem}.zip"
        archive_path = create_zip_archive(root / archive_name, generated_files, arc_root=output_dir)
        return build_download_response(
            archive_path,
            media_type="application/zip",
            extra_headers={"X-Operation-Message": result.get("message", "农残检测任务已完成")},
        )


@router.post("/monthly/execute")
async def execute_monthly_task_upload(
    month: str = Form(...),
    entries_json: str = Form(...),
    inspector_name: str = Form(default=""),
    use_saved_templates: str = Form(default="true"),
    big_template_file: UploadFile | None = File(default=None),
    small_template_file: UploadFile | None = File(default=None),
    big_template_path: str = Form(default=""),
    small_template_path: str = Form(default=""),
    output_dir: str = Form(default=""),
):
    entries = parse_json_form_value(
        entries_json,
        field_name="entries_json",
        expected_type=list,
    )
    normalized_entries = [
        {
            "date": str(item.get("date") or "").strip(),
            "names": [
                str(name).strip()
                for name in (item.get("names") or [])
                if str(name).strip()
            ],
        }
        for item in entries
        if isinstance(item, dict)
    ]
    if not normalized_entries:
        raise HTTPException(status_code=400, detail="月度清单为空，无法生成报告")

    if output_dir.strip():
        target_dir = Path(output_dir.strip())
        if not target_dir.is_dir():
            raise HTTPException(status_code=400, detail="输出目录不存在")

        resolved_big = Path(big_template_path.strip())
        resolved_small = Path(small_template_path.strip())
        if not resolved_big.exists():
            raise HTTPException(status_code=400, detail="大表模板路径无效")
        if not resolved_small.exists():
            raise HTTPException(status_code=400, detail="小表模板路径无效")

        result = await run_in_threadpool(
            service.execute_monthly_task,
            normalized_entries,
            str(resolved_big),
            str(resolved_small),
            month,
            str(target_dir),
            inspector_name,
        )

        generated_docx = sorted(
            p for p in target_dir.iterdir() if p.suffix.lower() == ".docx"
        )
        manifest_path = target_dir / "处理结果清单.json"
        manifest = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        return {
            "success": True,
            "message": result.get("message", "月度农残检测已完成"),
            "success_count": result.get("success_count", 0),
            "failure_count": result.get("failure_count", 0),
            "output_dir": str(target_dir),
            "generated_files": [str(p) for p in generated_docx],
            "manifest": manifest,
        }

    with tempfile.TemporaryDirectory(prefix="pesticide-monthly-") as tmpdir:
        root = Path(tmpdir)
        template_dir = root / "templates"
        output_dir_path = root / "output"
        output_dir_path.mkdir(parents=True, exist_ok=True)

        try:
            if big_template_path.strip():
                resolved_big_path = Path(big_template_path.strip())
            elif big_template_file is not None and big_template_file.filename:
                resolved_big_path = await save_upload(big_template_file, template_dir, "big-template")
            else:
                resolved_big_path = get_pesticide_template_path("big")

            if small_template_path.strip():
                resolved_small_path = Path(small_template_path.strip())
            elif small_template_file is not None and small_template_file.filename:
                resolved_small_path = await save_upload(small_template_file, template_dir, "small-template")
            else:
                resolved_small_path = get_pesticide_template_path("small")
        except FileNotFoundError as exc:
            if use_saved_templates.lower() == "false":
                raise HTTPException(status_code=400, detail="请上传本次使用的大小表模板") from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        result = await run_in_threadpool(
            service.execute_monthly_task,
            normalized_entries,
            str(resolved_big_path),
            str(resolved_small_path),
            month,
            str(output_dir_path),
            inspector_name,
        )

        generated_files = sorted(path for path in output_dir_path.iterdir() if path.is_file())
        generated_docx = [path for path in generated_files if path.suffix.lower() == ".docx"]
        if not generated_docx:
            detail = result.get("skipped", [{}])[0].get("reason") or "没有生成任何月度农残检测文件"
            raise HTTPException(status_code=400, detail=detail)

        archive_path = create_zip_archive(root / f"农残检测月度报告-{month}.zip", generated_files, arc_root=output_dir_path)
        return build_download_response(
            archive_path,
            media_type="application/zip",
            extra_headers={
                "X-Operation-Message": result.get("message", "月度农残检测已完成"),
                "X-Generated-Count": str(len(generated_docx)),
                "X-Skipped-Count": str(result.get("skipped_count", 0)),
            },
        )


@router.get("/templates/{kind}/versions",
            dependencies=[Depends(require_permission("pesticide:view"))])
async def list_template_versions(kind: str):
    kind = kind.strip().lower()
    if kind not in {"big", "small"}:
        raise HTTPException(status_code=400, detail="模板类型只能是 big 或 small")
    return {"kind": kind, "versions": get_pesticide_template_versions(kind)}


@router.post("/templates/{kind}/rollback",
             dependencies=[Depends(require_permission("pesticide:execute"))])
async def rollback_template(kind: str, version_date: str = Form(...)):
    kind = kind.strip().lower()
    try:
        result = rollback_pesticide_template(kind, version_date)
        return {"success": True, "templates": result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/templates/{kind}/versions/{version_date}",
               dependencies=[Depends(require_permission("pesticide:execute"))])
async def delete_template_version(kind: str, version_date: str):
    kind = kind.strip().lower()
    ok = delete_pesticide_template_version(kind, version_date)
    if not ok:
        raise HTTPException(status_code=404, detail="版本不存在")
    return {"success": True}
