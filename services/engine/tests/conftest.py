"""Shared pytest fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "api"))

from draftmaster_engine import ReportEngine, get_dataset  # noqa: E402


@pytest.fixture(scope="session")
def dataset():
    return get_dataset()


@pytest.fixture(scope="session")
def engine(dataset):
    return ReportEngine(dataset)


@pytest.fixture(scope="session")
def hero_ids(dataset):
    return {h["localized_name"]: h["id"] for h in dataset.heroes}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """FastAPI test client with a throwaway SQLite DB and in-memory cache.

    Isolation matters: the real app persists daily usage, so without a fresh DB
    per test the free-tier quota would leak across tests.
    """
    from fastapi.testclient import TestClient

    monkeypatch.setenv("DRAFTMASTER_DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("DRAFTMASTER_REDIS_URL", "")
    monkeypatch.setenv("DRAFTMASTER_ARTIFACT_PATH", str(_artifact()))
    # A deterministic signing key lets the billing tests mint real premium
    # sessions without touching the network.
    monkeypatch.setenv("DRAFTMASTER_SECRET_KEY", "test-signing-secret")

    import draftmaster_api.config as config

    config.get_settings.cache_clear()

    from draftmaster_api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
    config.get_settings.cache_clear()


def _artifact():
    return ROOT / "data" / "artifacts" / "draftmaster-data.json"
