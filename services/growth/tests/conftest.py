"""Shared fixtures for the growth-engine tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "growth"))

from draftmaster_engine import get_dataset  # noqa: E402

from draftmaster_growth.config import GrowthConfig  # noqa: E402


@pytest.fixture(scope="session")
def dataset():
    return get_dataset()


@pytest.fixture()
def settings(tmp_path):
    cfg = GrowthConfig.from_env()
    cfg.state_path = str(tmp_path / "state.json")
    cfg.output_dir = str(tmp_path / "out")
    cfg.allow_publish = False
    return cfg


@pytest.fixture()
def agent(settings, dataset):
    from draftmaster_growth.agent import GrowthAgent

    return GrowthAgent(settings, dataset)
