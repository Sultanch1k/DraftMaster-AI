"""Screenshot analyzer endpoint."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from draftmaster_engine.i18n import localize, localize_report

from ..locale import resolve_locale
from ..schemas import UsageOut
from .analysis import _enforce_quota, _quota_signature

router = APIRouter(tags=["screenshot"])

MAX_BYTES = 8 * 1024 * 1024


@router.post("/screenshot/analyse")
async def analyse_screenshot(request: Request, file: UploadFile = File(...)) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty upload")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="image too large (max 8 MB)")

    locale = resolve_locale(request)
    analyzer = request.app.state.screenshot
    try:
        detection = analyzer.analyse(data)
    except Exception:
        # Pillow raises a wide range of internal errors; never leak them — the
        # user only needs to know the file could not be read as an image.
        raise HTTPException(status_code=422, detail="could not read image")

    hero_ids = detection["hero_ids"][:5]
    usage = _enforce_quota(request, _quota_signature("screenshot", hero_ids))
    report = None
    if hero_ids:
        report = localize_report(request.app.state.engine.analyse(enemy_ids=hero_ids).to_dict(), locale)

    return localize({
        "detection": detection,
        "report": report,
        "usage": usage.model_dump(),
        "note": (
            "Detected heroes were auto-fed into the report engine."
            if hero_ids
            else "No heroes detected — try a clearer, larger screenshot of the draft screen."
        ),
    }, locale)
