"""DraftMaster AI autonomous growth engine.

A deterministic, dependency-light system that grows the product without a human
in the loop for the day-to-day work: it decides what to publish, writes the
content, ships it to the channels it is allowed to ship to, measures what
happened, and changes its own future decisions based on the results.

Design rules (mirrors the strategy engine):

* **Pure and deterministic.** Given the same plan date, dataset and store the
  agent produces the same plan. No wall-clock or random state leaks into the
  decision path — ``random`` is never used; exploration is a deterministic
  rotating schedule so a dry run is reproducible and reviewable.
* **Safe by default.** Every external side effect (a network post, a partner
  email) is a *channel adapter* that must be explicitly enabled and
  credentialed. With no credentials the adapters run in ``dry_run`` and record
  exactly what they *would* have sent. A fresh clone can therefore run the whole
  loop end to end and inspect the output.
* **Measured, then improved.** Every published piece is a variant. Outcomes are
  attributed back to the variant and a deterministic bandit shifts future
  weight toward whatever is actually working.
"""
from __future__ import annotations

from .agent import GrowthAgent
from .config import GrowthConfig
from .store import GrowthStore

__all__ = ["GrowthAgent", "GrowthConfig", "GrowthStore"]
__version__ = "1.0.0"
