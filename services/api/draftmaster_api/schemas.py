"""Pydantic request/response schemas for the DraftMaster AI API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyseRequest(BaseModel):
    enemy_hero_ids: list[int] = Field(..., min_length=1, max_length=5)
    hero_id: int | None = None
    role: str | None = None
    rank_tier: int | None = Field(default=None, ge=0, le=85)
    allies: list[int] = Field(default_factory=list, max_length=4)
    comfort: dict[int, float] = Field(default_factory=dict)
    locale: str | None = None


class PanicRequest(BaseModel):
    enemy_hero_ids: list[int] = Field(..., min_length=1, max_length=5)
    role: str | None = None
    rank_tier: int | None = Field(default=None, ge=0, le=85)
    comfort: dict[int, float] = Field(default_factory=dict)
    locale: str | None = None


class WinProbRequest(BaseModel):
    enemy_hero_ids: list[int] = Field(..., min_length=1, max_length=5)
    hero_id: int
    role: str | None = None
    rank_tier: int | None = Field(default=None, ge=0, le=85)


class MatchCoachRequest(BaseModel):
    match_id: int = Field(..., gt=0)
    account_id: int | None = None


class ProfileUpsert(BaseModel):
    user_id: str
    role: str | None = None
    rank_tier: int | None = None
    favorite_heroes: list[int] = Field(default_factory=list)
    comfort: dict[int, float] = Field(default_factory=dict)
    playstyle: str | None = None


class HeroOut(BaseModel):
    id: int
    name: str
    localized_name: str
    roles: list[str]
    primary_attr: str | None = None
    attack_type: str | None = None
    icon: str | None = None
    img: str | None = None
    tags: list[str] = Field(default_factory=list)
    pub_winrate: float | None = None


class HealthOut(BaseModel):
    status: str
    version: str
    environment: str
    hero_count: int
    patch: str | None = None
    dataset_generated_at: str | None = None


class UsageOut(BaseModel):
    plan: Literal["free", "premium"]
    used_today: int
    daily_limit: int | None
    remaining: int | None


class ApiError(BaseModel):
    detail: str
    code: str | None = None


class AnalysisResponse(BaseModel):
    report: dict[str, Any]
    usage: UsageOut | None = None
