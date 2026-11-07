"""Match ID coach + personal AI coach endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..schemas import MatchCoachRequest, ProfileUpsert

router = APIRouter(tags=["coach"])


@router.post("/match/coach")
def match_coach(payload: MatchCoachRequest, request: Request) -> dict:
    cache = request.app.state.cache
    settings = request.app.state.settings
    key = f"match:{payload.match_id}:{payload.account_id}"
    cached = cache.get(key)
    if cached:
        cached["cached"] = True
        return cached
    try:
        report = request.app.state.coach.coach(payload.match_id, payload.account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:  # network / upstream
        raise HTTPException(status_code=502, detail=f"OpenDota request failed: {exc}")
    body = {"coach_report": report.to_dict(), "cached": False}
    cache.set(key, body, settings.match_cache_ttl_seconds)
    return body


@router.get("/match/{match_id}")
def match_summary(match_id: int, request: Request) -> dict:
    try:
        match = request.app.state.coach.client.match(match_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenDota request failed: {exc}")
    if "players" not in match:
        raise HTTPException(status_code=404, detail="match not available")
    ds = request.app.state.engine.ds
    return {
        "match_id": match_id,
        "duration_min": round((match.get("duration") or 0) / 60.0, 1),
        "radiant_win": match.get("radiant_win"),
        "players": [
            {
                "hero_id": p.get("hero_id"),
                "hero": (ds.by_id.get(p.get("hero_id")) or {}).get("localized_name"),
                "isRadiant": p.get("isRadiant"),
                "kills": p.get("kills"),
                "deaths": p.get("deaths"),
                "assists": p.get("assists"),
                "gpm": p.get("gold_per_min"),
                "xpm": p.get("xp_per_min"),
                "net_worth": p.get("net_worth"),
            }
            for p in match["players"]
        ],
    }


@router.put("/profile")
def upsert_profile(payload: ProfileUpsert, request: Request) -> dict:
    return request.app.state.store.upsert_profile(payload.model_dump())


@router.get("/profile/{user_id}")
def get_profile(user_id: str, request: Request) -> dict:
    profile = request.app.state.store.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    return profile
