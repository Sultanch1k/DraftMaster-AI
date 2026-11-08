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


class ActivateRequest(BaseModel):
    license_key: str = Field(..., min_length=4, max_length=512)


class SessionOut(BaseModel):
    token: str = ""
    plan: Literal["free", "premium"] = "free"
    email: str = ""
    status: str = "free"


class BillingConfigOut(BaseModel):
    enabled: bool
    checkout_url: str = ""
    support_email: str = ""
    free_daily_analyses: int
    currency: str = "USD"
    price_monthly: str = ""
    price_annual: str = ""


class EventIn(BaseModel):
    """A single client-side funnel event (best-effort, no PII beyond user id)."""

    name: str = Field(..., min_length=1, max_length=64)
    user_id: str | None = None
    props: dict[str, Any] = Field(default_factory=dict)


class EventBatch(BaseModel):
    events: list[EventIn] = Field(..., max_length=50)


class SubscribeRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    user_id: str | None = None
    source: str | None = None


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
    # Exposed so a deploy can be verified as durable from outside: "memory"
    # here in production means entitlements will not survive a restart.
    store_backend: str | None = None
    store_detail: str | None = None
    cache_backend: str | None = None


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
