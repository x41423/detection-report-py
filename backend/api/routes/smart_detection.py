from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from backend.auth.dependencies import require_permission
from backend.models.schemas import (
    SmartRecommendResponse, SmartExecuteRequest, SmartExecuteResponse,
    BackfillRequest, BackfillResponse, GapResponse, PrepareResponse,
)
from backend.services.smart_detection_service import SmartDetectionService
from backend.services.gap_detection_service import GapDetectionService
from backend.services.config_service import get_config

router = APIRouter()
detection_service = SmartDetectionService()


def _get_gap_service() -> GapDetectionService:
    cfg = get_config()
    return GapDetectionService(output_root=cfg.get("output_dir", ""))


@router.get("/smart/recommend", response_model=SmartRecommendResponse,
            dependencies=[Depends(require_permission("pesticide:view"))])
async def smart_recommend(target_date: str = Query(None)):
    if target_date:
        try:
            dt = date.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    else:
        dt = date.today()

    result = detection_service.recommend(dt)
    return SmartRecommendResponse(**result)


@router.get("/smart/prepare", response_model=PrepareResponse,
            dependencies=[Depends(require_permission("pesticide:view"))])
async def smart_prepare():
    """Return templates and output config for the detection workflow."""
    cfg = get_config()
    try:
        from backend.services.template_library_service import get_pesticide_template_path
        big_template = str(get_pesticide_template_path("big"))
    except FileNotFoundError:
        big_template = ""
    try:
        small_template = str(get_pesticide_template_path("small"))
    except FileNotFoundError:
        small_template = ""

    return PrepareResponse(
        big_template=big_template,
        small_template=small_template,
        output_dir=cfg.get("output_dir", ""),
        inspector_name=cfg.get("inspector_name", "检测员"),
    )


@router.put("/smart/prepare", response_model=PrepareResponse,
           dependencies=[Depends(require_permission("pesticide:execute"))])
async def smart_prepare_update(inspector_name: str = Query(..., min_length=1)):
    """Update inspector_name in config."""
    from backend.services.config_service import update_config
    update_config({"inspector_name": inspector_name})
    return await smart_prepare()


@router.post("/smart/execute", response_model=SmartExecuteResponse,
             dependencies=[Depends(require_permission("pesticide:execute"))])
async def smart_execute(req: SmartExecuteRequest):
    result = detection_service.execute(req.model_dump())
    return SmartExecuteResponse(**result)


@router.get("/smart/gaps", response_model=GapResponse,
            dependencies=[Depends(require_permission("pesticide:view"))])
async def smart_gaps(days: int = Query(default=7, ge=1, le=365)):
    gap_svc = _get_gap_service()
    missing = gap_svc.detect_recent_gaps(days=days)
    return GapResponse(
        missing_dates=[d.isoformat() for d in missing],
        last_detection_date=None,
        total_missing=len(missing),
    )


@router.post("/smart/backfill", response_model=BackfillResponse,
             dependencies=[Depends(require_permission("pesticide:execute"))])
async def smart_backfill(req: BackfillRequest):
    try:
        start = date.fromisoformat(req.start_date)
        end = date.fromisoformat(req.end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    gap_svc = _get_gap_service()
    missing = gap_svc.detect_gaps(start, end)

    try:
        from backend.services.template_library_service import get_pesticide_template_path
        big_template = str(get_pesticide_template_path("big"))
        small_template = str(get_pesticide_template_path("small"))
    except FileNotFoundError:
        return BackfillResponse(success=False, results=[{"error": "模板未设置"}])

    cfg = get_config()
    output_dir = cfg.get("output_dir", "")

    results = []
    for d in missing:
        try:
            result = detection_service.execute({
                "selected_varieties": [],
                "date": d.isoformat(),
                "big_template": big_template,
                "small_template": small_template,
                "output_dir": output_dir,
                "inspector_name": req.inspector_name,
            })
            results.append({
                "date": d.isoformat(),
                "success": result.get("success", False),
                "error": result.get("error"),
            })
        except Exception as e:
            results.append({"date": d.isoformat(), "success": False, "error": str(e)})

    return BackfillResponse(success=True, results=results)
