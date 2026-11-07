"""Screenshot analyzer endpoint."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from ..schemas import UsageOut
from .analysis import _enforce_quota

router = APIRouter(tags=["screenshot"])

MAX_BYTES = 8 * 1024 * 1024


@router.post("/screenshot/analyse")
async def analyse_screenshot(request: Request, file: UploadFile = File(...)) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty upload")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="image too large (max 8 MB)")

    usage = _enforce_quota(request)
    analyzer = request.app.state.screenshot
    try:
        detection = analyzer.analyse(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"could not read image: {exc}")

    hero_ids = detection["hero_ids"][:5]
    report = None
    if hero_ids:
        report = request.app.state.engine.analyse(enemy_ids=hero_ids).to_dict()

    return {
        "detection": detection,
        "report": report,
        "usage": usage.model_dump(),
        "note": (
            "Detected heroes were auto-fed into the report engine."
            if hero_ids
            else "No heroes detected — try a clearer, larger screenshot of the draft screen."
        ),
    }
