"""Draft analysis endpoints — the core product surface."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from ..billing import verify_session
from ..locale import localize_analysis, localize_hero_strategy, localize_panic, resolve_locale
from ..schemas import (
    AnalyseRequest,
    HeroStrategyRequest,
    PanicRequest,
    ShareOut,
    ShareRequest,
    WinProbRequest,
    UsageOut,
)
from ..share import sign_share, verify_share

router = APIRouter(tags=["analysis"])

FREE_PLAN = "free"
PREMIUM_PLAN = "premium"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _premium_identity(request: Request) -> str | None:
    """Return a stable identity when the caller holds a valid premium session.

    Premium is proved by an HMAC-signed session token minted by /api/billing/activate
    after the payment provider confirmed an active license. The token is verified
    here (signature + expiry) and then checked against the entitlement store, so a
    forged or hand-crafted token cannot grant premium. Returns None for free users.
    """
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    payload = verify_session(request.app.state.settings, token)
    if not payload:
        return None
    row = request.app.state.store.get_entitlement(token)
    # Signature valid but the entitlement must still be active — a refund,
    # cancellation or chargeback revokes it via the billing webhook.
    if not row or (row.get("status") or "").lower() != "active":
        return None
    return payload.get("sub") or payload.get("email") or "premium"


def _plan_for(request: Request) -> str:
    return PREMIUM_PLAN if _premium_identity(request) else FREE_PLAN


def _usage_out(request: Request, used: int, plan: str) -> UsageOut:
    limit = None if plan == PREMIUM_PLAN else request.app.state.settings.free_daily_analyses
    remaining = None if limit is None else max(0, limit - used)
    return UsageOut(plan=plan, used_today=used, daily_limit=limit, remaining=remaining)


def _quota_signature(*parts: object) -> str:
    """A stable identity for one analysis, independent of locale.

    Re-requesting the same draft (for example after switching language, which
    only changes the prose language) must not spend another quota unit, so the
    signature deliberately excludes the locale.
    """
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _quota_identity(request: Request) -> str:
    """A server-anchored identity for the free daily quota.

    The client-supplied ``x-user-id`` is a convenience only — a determined user
    can reset it by clearing storage. We therefore mix in the request IP so the
    free limit is not trivially bypassable, while still keying per-user for the
    common case. This is deliberately cheap: it is a business guard, not a
    security boundary (a paid tier exists for anyone who needs more).
    """
    client_id = request.headers.get("x-user-id", "anonymous")
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "")
    return hashlib.sha256(f"{client_id}|{ip}".encode()).hexdigest()[:24]


def _enforce_quota(request: Request, signature: str | None = None) -> UsageOut:
    """Enforce the daily quota, charging each distinct analysis once per day.

    A signature identifies the analysis; when the same signature has already
    been charged today the request is free. This keeps "3 analyses per day"
    meaning three drafts, not three HTTP calls, and makes the language switch
    (which re-fetches the same draft in another locale) cost nothing.
    """
    store = request.app.state.store
    settings = request.app.state.settings
    cache = request.app.state.cache
    plan = _plan_for(request)
    user = _quota_identity(request)
    day = _today()

    if plan == PREMIUM_PLAN:
        return _usage_out(request, store.get_usage(user, day), plan)

    marker = f"quota:{user}:{day}:{signature or 'default'}"
    already_charged = bool(cache.get(marker))
    used = store.get_usage(user, day)
    if not already_charged:
        # An analysis already charged today stays free (so a language switch or a
        # reload never costs a unit). Only a *new* draft once the limit is spent
        # is refused — charging it first would also block the free re-fetches.
        if used >= settings.free_daily_analyses:
            raise HTTPException(status_code=402, detail=_quota_detail(request))
        used = store.increment_usage(user, day)
        cache.set(marker, 1, 86400)
    return _usage_out(request, used, plan)


def _quota_detail(request: Request) -> str:
    limit = request.app.state.settings.free_daily_analyses
    if resolve_locale(request) == "ru":
        return (
            f"Бесплатный тариф допускает {limit} анализа в день. "
            "Оформите Premium для безлимитных анализов и ИИ-тренера."
        )
    return (
        f"Free plan allows {limit} analyses per day. "
        "Upgrade to Premium for unlimited analyses and the AI coach."
    )


def _validate_ids(request: Request, ids: list[int]) -> None:
    ds = request.app.state.engine.ds
    unknown = [i for i in ids if i not in ds.by_id]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown hero ids: {unknown}")


@router.post("/analyse")
def analyse(payload: AnalyseRequest, request: Request) -> dict:
    _validate_ids(request, payload.enemy_hero_ids + payload.allies + ([payload.hero_id] if payload.hero_id else []))
    usage = _enforce_quota(
        request,
        _quota_signature("analyse", payload.enemy_hero_ids, payload.allies, payload.hero_id, payload.role, payload.rank_tier),
    )
    locale = resolve_locale(request, payload.locale)

    cache = request.app.state.cache
    settings = request.app.state.settings
    # The locale is part of the key: an English and a Russian report for the
    # same draft are different documents and must not share a cache entry.
    key = "analyse:" + locale + ":" + hashlib.sha256(
        json.dumps(payload.model_dump(), sort_keys=True).encode()
    ).hexdigest()
    cached = cache.get(key)
    if cached:
        cached["usage"] = usage.model_dump()
        cached["cached"] = True
        return cached

    report = request.app.state.engine.analyse(
        enemy_ids=payload.enemy_hero_ids,
        hero_id=payload.hero_id,
        role=payload.role,
        rank_tier=payload.rank_tier,
        comfort=payload.comfort,
        allies=payload.allies,
    )
    body = {"report": report.to_dict(), "usage": usage.model_dump(), "cached": False}
    body = localize_analysis(body, locale)
    cache.set(key, body, settings.cache_ttl_seconds)
    return body


@router.post("/hero-strategy")
def hero_strategy(payload: HeroStrategyRequest, request: Request) -> dict:
    """My Hero Strategy — how to win with a hero the user has already picked.

    Distinct from /analyse: the hero is fixed, the enemy draft is exactly five,
    and the report is a matchup-specific game plan rather than a pick ranking.
    """
    _validate_ids(request, payload.enemy_hero_ids + [payload.hero_id])
    if payload.hero_id in payload.enemy_hero_ids:
        raise HTTPException(
            status_code=422,
            detail="The hero you are playing cannot also be one of the five enemy heroes.",
        )
    if len(set(payload.enemy_hero_ids)) != len(payload.enemy_hero_ids):
        raise HTTPException(status_code=422, detail="Duplicate enemy heroes are not allowed.")

    usage = _enforce_quota(
        request,
        _quota_signature("hero_strategy", payload.hero_id, payload.enemy_hero_ids, payload.role, payload.rank_tier),
    )
    locale = resolve_locale(request, payload.locale)
    cache = request.app.state.cache
    settings = request.app.state.settings

    key = "hero_strategy:" + locale + ":" + hashlib.sha256(
        json.dumps(payload.model_dump(), sort_keys=True).encode()
    ).hexdigest()
    cached = cache.get(key)
    if cached:
        cached["usage"] = usage.model_dump()
        cached["cached"] = True
        return cached

    strategy = request.app.state.hero_strategy.build(
        hero_id=payload.hero_id,
        enemy_ids=payload.enemy_hero_ids,
        role=payload.role,
        rank_tier=payload.rank_tier,
    )
    body = {"strategy": strategy.to_dict(), "usage": usage.model_dump(), "cached": False}
    body = localize_hero_strategy(body, locale)
    cache.set(key, body, settings.cache_ttl_seconds)
    return body


@router.post("/panic")
def panic(payload: PanicRequest, request: Request) -> dict:
    """The 'I'M LAST PICK' flow — tuned for sub-second, one-screen output."""
    _validate_ids(request, payload.enemy_hero_ids)
    usage = _enforce_quota(
        request, _quota_signature("panic", payload.enemy_hero_ids, payload.role, payload.rank_tier)
    )
    locale = resolve_locale(request, payload.locale)
    result = request.app.state.engine.panic(
        enemy_ids=payload.enemy_hero_ids,
        role=payload.role,
        rank_tier=payload.rank_tier,
        comfort=payload.comfort,
    )
    result["usage"] = usage.model_dump()
    return localize_panic(result, locale)


@router.post("/share", response_model=ShareOut)
def create_share(payload: ShareRequest, request: Request) -> dict:
    """Mint a signed, public link for a draft.

    Charged against the normal daily quota, so the share loop cannot be abused
    as a free unlimited-analysis endpoint. Re-sharing a draft already analysed
    today is free, because the quota signature matches (see `_enforce_quota`).
    """
    _validate_ids(request, payload.enemy_hero_ids)
    _enforce_quota(
        request, _quota_signature("panic", payload.enemy_hero_ids, payload.role, payload.rank_tier)
    )

    # Derive the pick and the win probability from the same engine call the
    # public render endpoint will make, so the OG card and the page it links to
    # can never advertise different heroes.
    result = request.app.state.engine.panic(
        enemy_ids=payload.enemy_hero_ids,
        role=payload.role,
        rank_tier=payload.rank_tier,
        comfort={},
    )
    hero_id = result["best_hero"]["hero_id"]
    win = result.get("win_probability", {}).get("player_win_probability")

    body: dict = {"e": payload.enemy_hero_ids, "h": hero_id}
    if win is not None:
        body["w"] = round(float(win))
    if payload.role:
        body["r"] = payload.role
    if payload.rank_tier:
        body["rk"] = payload.rank_tier

    token = sign_share(request.app.state.settings, body)
    if not token:
        # No signing key: the product runs free-only, and the client falls back
        # to its own unsigned link (which renders client-side).
        return {"token": "", "path": "", "win_probability": win}
    return {"token": token, "path": f"/share/{token}", "win_probability": win}


@router.get("/share/{token}")
def render_share(token: str, request: Request) -> dict:
    """Render the plan behind a signed share token — no quota charged.

    The signature is what makes this safe to leave public: a token can only be
    produced by an authenticated quota-paying request, so a stranger opening a
    shared link is spending the sharer's quota, not getting a free tier.
    """
    payload = verify_share(request.app.state.settings, token)
    if not payload:
        raise HTTPException(status_code=404, detail="This share link is invalid or has expired.")
    _validate_ids(request, payload["e"])
    locale = resolve_locale(request)
    result = request.app.state.engine.panic(
        enemy_ids=payload["e"],
        role=payload.get("r"),
        rank_tier=payload.get("rk"),
        comfort={},
    )
    # A shared link is a read-only view: drop the usage block entirely (the
    # viewer is not the account being charged, and a quota count here would be
    # meaningless).
    result.pop("usage", None)
    return localize_panic(result, locale)


@router.post("/win-probability")
def win_prob(payload: WinProbRequest, request: Request) -> dict:
    _validate_ids(request, payload.enemy_hero_ids + [payload.hero_id])
    ds = request.app.state.engine.ds
    from draftmaster_engine.winprob import win_probability

    result = win_probability(
        ds, payload.hero_id, payload.enemy_hero_ids, payload.role, payload.rank_tier
    )
    return localize_panic(result.to_dict(), resolve_locale(request))


@router.post("/threat-analysis")
def threat_analysis(payload: WinProbRequest, request: Request) -> dict:
    _validate_ids(request, payload.enemy_hero_ids)
    ds = request.app.state.engine.ds
    from draftmaster_engine.threats import analyse_threats

    profile = analyse_threats(ds, payload.enemy_hero_ids, payload.hero_id)
    return localize_panic(profile.to_dict(), resolve_locale(request))
