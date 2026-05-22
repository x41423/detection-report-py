from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.services.mimo_service import MimoService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/mimo/status")
async def mimo_status():
    svc = MimoService()
    return {
        "configured": svc.available,
        "model": svc.model if svc.available else None,
        "message": "MiMo API 已就绪" if svc.available else "MiMo API 未配置（设置 MIMO_API_KEY 和 MIMO_ENABLED=true）",
    }


@router.post("/mimo/echo")
async def mimo_echo(text: str = ""):
    if not text:
        return {"echo": None}
    svc = MimoService()
    result = svc.chat([
        {"role": "user", "content": f"请用一句话回复：{text}"},
    ])
    if result:
        try:
            reply = result["choices"][0]["message"]["content"]
            return {"echo": reply}
        except (KeyError, IndexError):
            pass
    return {"echo": f"[MiMo 未响应] {text}"}
