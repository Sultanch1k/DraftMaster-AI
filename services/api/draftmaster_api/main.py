"""DraftMaster AI API application factory."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from draftmaster_engine import MatchCoach, ReportEngine, ScreenshotAnalyzer, get_dataset

from .config import get_settings
from .infra import Cache, Store
from .routers import analysis, coach, reference, screenshot
from .schemas import HealthOut

log = logging.getLogger("draftmaster")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("loading dataset from %s", settings.artifact_path)
    dataset = get_dataset(settings.artifact_path)
    app.state.settings = settings
    app.state.engine = ReportEngine(dataset)
    app.state.cache = Cache(settings)
    app.state.store = Store(settings)
    app.state.coach = MatchCoach(dataset)
    try:
        app.state.screenshot = ScreenshotAnalyzer(settings.hero_hashes_path)
        app.state.screenshot._load()
        log.info("screenshot analyzer ready (%d hero signatures)", len(app.state.screenshot.signatures))
    except Exception as exc:
        log.warning("screenshot analyzer unavailable: %s", exc)
        app.state.screenshot = None
    log.info("cache backend=%s store backend=%s", app.state.cache.backend, app.state.store.backend)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=(
            "DraftMaster AI — the Dota 2 AI coach that tells you how to win the game, "
            "not just which hero to pick. One Click Win Plan, WIN PROBABILITY ENGINE, "
            "dynamic item builder, screenshot analysis and match coaching."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def timing(request: Request, call_next):
        import time

        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
        return response

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        return JSONResponse(status_code=422, content={"detail": str(exc), "code": "invalid_hero"})

    @app.get("/health", response_model=HealthOut, tags=["system"])
    def health(request: Request) -> dict:
        ds = request.app.state.engine.ds
        return {
            "status": "ok",
            "version": settings.version,
            "environment": settings.environment,
            "hero_count": len(ds.heroes),
            "patch": (ds.patch or {}).get("name"),
            "dataset_generated_at": ds.generated_at,
        }

    @app.get("/", tags=["system"])
    def root() -> dict:
        return {
            "name": settings.app_name,
            "tagline": "Here is exactly how to win this specific game.",
            "docs": "/docs",
            "flagship": ["POST /api/panic", "POST /api/analyse", "POST /api/win-probability"],
        }

    app.include_router(reference.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(screenshot.router, prefix="/api")
    app.include_router(coach.router, prefix="/api")
    return app


app = create_app()
