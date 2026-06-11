from fastapi import APIRouter, Depends, HTTPException
from backend.auth.dependencies import require_permission
from backend.models.schemas import ConfigResponse, ConfigUpdateRequest
from backend.services.config_service import get_config, update_config

router = APIRouter()


@router.get("/", response_model=ConfigResponse, dependencies=[Depends(require_permission("config:view"))])
def get_full_config():
    """获取完整配置"""
    return ConfigResponse(config=get_config())


@router.put("/", response_model=ConfigResponse, dependencies=[Depends(require_permission("config:update"))])
def update_config_data(req: ConfigUpdateRequest):
    """更新配置"""
    cfg = update_config(req.updates)
    return ConfigResponse(config=cfg)
