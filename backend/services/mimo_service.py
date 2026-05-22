from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


class MimoService:
    """MiMo API integration service.

    Wraps the Xiaomi MiMo API (OpenAI-compatible) for chat completion,
    detection report analysis, and future ASR integration.

    TIP: To remove after application approval:
      - Delete this file
      - Delete backend/api/routes/mimo.py
      - Revert the single line added in backend/main.py
      - Revert the MiMo block in smart_detection_service.py
      - Clean up .env.local.example MiMo section
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("MIMO_API_KEY", "")
        self.api_base = (os.getenv("MIMO_API_BASE") or "https://platform.xiaomimimo.com").rstrip("/")
        self.model = os.getenv("MIMO_MODEL", "MiMo-V2.5-72B")

    @property
    def available(self) -> bool:
        enabled = os.getenv("MIMO_ENABLED", "").strip().lower() in ("1", "true", "yes")
        return enabled and bool(self.api_key)

    def chat(self, messages: list[dict], **kwargs: Any) -> dict[str, Any] | None:
        if not self.available:
            logger.debug("MiMo not configured, skipping chat call")
            return None
        try:
            resp = requests.post(
                f"{self.api_base}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": messages,
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_tokens": kwargs.get("max_tokens", 2048),
                },
                timeout=kwargs.get("timeout", 60),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("MiMo API call failed: %s", e)
            return None

    def analyze_rates(self, varieties: list[str], rates: dict[str, Any]) -> str | None:
        prompt = (
            "你是一个农产品质量检测分析专家。以下是一批蔬菜的检测数据，"
            "请分析是否存在异常值，并给出简要结论（50字以内）：\n"
            f"品种：{', '.join(varieties)}\n"
            f"检测数据：{json.dumps(rates, ensure_ascii=False, indent=2)}"
        )
        result = self.chat([
            {"role": "system", "content": "你是小米 MiMo V2.5 驱动的检测分析助手。"},
            {"role": "user", "content": prompt},
        ])
        if result:
            try:
                return result["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                return None
        return None
