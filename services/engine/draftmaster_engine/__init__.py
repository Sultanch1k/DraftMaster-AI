"""DraftMaster AI strategy engine.

Pure-Python, dependency-light strategy core. Consumes the OpenDota-derived
artifact produced by tools/pipeline/build_datasets.py and turns an enemy draft
into an actionable, per-game win plan.
"""
from __future__ import annotations

from .dataset import Dataset, get_dataset
from .report import ReportEngine
from .coach import MatchCoach, OpenDotaClient
from .screenshot import ScreenshotAnalyzer

__all__ = [
    "Dataset",
    "get_dataset",
    "ReportEngine",
    "MatchCoach",
    "OpenDotaClient",
    "ScreenshotAnalyzer",
]
__version__ = "1.0.0"
