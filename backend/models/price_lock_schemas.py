"""Pydantic models for Price Lock (限时锁价)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PriceLockItemCreate(BaseModel):
    veg_name: str = Field(..., min_length=1, max_length=200)
    locked_price: float = Field(default=0, ge=0)


class PriceLockItemResponse(BaseModel):
    id: int
    veg_name: str
    locked_price: float


class PriceLockCreate(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=200)
    salemenu_id: str | None = None
    salemenu_name: str | None = None
    target_count: int = Field(default=0, ge=0)
    start_time: str | None = None
    end_time: str | None = None
    items: list[PriceLockItemCreate] = Field(default_factory=list)


class PriceLockUpdate(BaseModel):
    rule_name: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class PriceLockResponse(BaseModel):
    id: int
    rule_code: str
    rule_name: str
    salemenu_id: str | None
    salemenu_name: str | None
    target_count: int
    category_count: int
    start_time: str | None
    end_time: str | None
    status: str
    operator: str | None
    items: list[PriceLockItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
