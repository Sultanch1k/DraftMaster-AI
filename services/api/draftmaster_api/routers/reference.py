"""Hero, item and meta reference endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..schemas import HeroOut

router = APIRouter(tags=["reference"])


@router.get("/heroes", response_model=list[HeroOut])
def list_heroes(request: Request) -> list[dict]:
    return request.app.state.engine.hero_list()


@router.get("/heroes/{hero_id}")
def get_hero(hero_id: str, request: Request) -> dict:
    ds = request.app.state.engine.ds
    hero = ds.hero(int(hero_id)) if hero_id.isdigit() else ds.hero(hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail=f"hero {hero_id} not found")
    return hero


@router.get("/heroes/{hero_id}/matchups")
def hero_matchups(hero_id: int, request: Request) -> dict:
    ds = request.app.state.engine.ds
    if hero_id not in ds.by_id:
        raise HTTPException(status_code=404, detail="hero not found")
    row = ds.counter.get(hero_id, {})
    ranked = sorted(row.items(), key=lambda kv: -kv[1])
    return {
        "hero_id": hero_id,
        "hero": ds.by_id[hero_id]["localized_name"],
        "best_against": [
            {"hero_id": h, "hero": ds.by_id[h]["localized_name"], "score": round(50 + v * 120, 1)}
            for h, v in ranked[:10]
            if h in ds.by_id
        ],
        "worst_against": [
            {"hero_id": h, "hero": ds.by_id[h]["localized_name"], "score": round(50 + v * 120, 1)}
            for h, v in ranked[-10:]
            if h in ds.by_id
        ],
    }


@router.get("/items")
def list_items(request: Request) -> list[dict]:
    return request.app.state.engine.item_list()


@router.get("/meta")
def meta(request: Request) -> dict:
    ds = request.app.state.engine.ds
    heroes = ds.heroes
    trending = sorted(heroes, key=lambda h: -(h.get("pub_pick") or 0))[:15]
    winners = sorted(heroes, key=lambda h: -(h.get("cm_winrate") or 0))[:15]
    losers = sorted(heroes, key=lambda h: (h.get("cm_winrate") or 1))[:15]
    return {
        "patch": (ds.patch or {}).get("name"),
        "generated_at": ds.generated_at,
        "source": "OpenDota public match data",
        "trending": [
            {"hero_id": h["id"], "hero": h["localized_name"], "picks": h.get("pub_pick")}
            for h in trending
        ],
        "patch_winners": [
            {"hero_id": h["id"], "hero": h["localized_name"], "cm_winrate": h.get("cm_winrate")}
            for h in winners
        ],
        "patch_losers": [
            {"hero_id": h["id"], "hero": h["localized_name"], "cm_winrate": h.get("cm_winrate")}
            for h in losers
        ],
    }
