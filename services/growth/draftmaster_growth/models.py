"""Value objects shared across the growth engine.

Kept as plain dataclasses (no pydantic) so the engine stays import-light and
serialisable with ``asdict`` — the same convention the strategy engine uses.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Variant:
    """A single content variant the optimizer can choose between.

    A variant is a *style*, not a piece of content: "hook-first short post" vs
    "question post". The content engine renders the chosen variant for a topic.
    """

    key: str
    description: str
    # Purely presentational knobs the renderer understands.
    style: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentItem:
    """A rendered, publishable piece of content."""

    item_id: str
    kind: str  # "post" | "thread" | "blog" | "outreach" | "video_script" | "patch_report"
    topic: str
    # The topic's full identity (topic + data + locale). Dedupe keys off this,
    # not off ``topic``, so the same subject in another locale is still new.
    signature: str
    title: str
    body: str
    locale: str  # "en" | "ru"
    variant: str
    channel: str
    hashtags: list[str] = field(default_factory=list)
    media: dict[str, Any] = field(default_factory=dict)
    # The product links a piece should carry. Kept explicit so the renderer
    # never has to guess a URL.
    links: dict[str, str] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PublishResult:
    """Outcome of attempting to publish one item to one channel."""

    item_id: str
    channel: str
    ok: bool
    live: bool  # True => actually sent; False => dry run
    external_id: str = ""
    detail: str = ""
    payload_preview: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MetricSample:
    """A measured outcome for a published item, fed back to the optimizer."""

    item_id: str
    variant: str
    topic: str
    channel: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    # Anything else the channel reports (likes, saves, shares...).
    extra: dict[str, int] = field(default_factory=dict)
    measured_at: str = ""

    @property
    def ctr(self) -> float:
        return (self.clicks / self.impressions) if self.impressions else 0.0

    @property
    def cvr(self) -> float:
        return (self.conversions / self.clicks) if self.clicks else 0.0

    @property
    def score(self) -> float:
        """Single scalar the bandit optimises.

        Clicks dominate (traffic is the growth lever) but a conversion is worth
        far more, so it is weighted heavily. A small floor on impressions keeps
        a lucky 1-impression sample from dominating.
        """
        return self.clicks + 10.0 * self.conversions

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Prospect:
    """A partner/creator the outreach engine is working."""

    key: str
    name: str
    platform: str
    handle: str = ""
    followers: int = 0
    audience: str = ""
    status: str = "new"  # new | contacted | replied | won | lost
    touches: int = 0
    last_touch: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OutreachMessage:
    prospect: Prospect
    subject: str
    body: str
    locale: str

    def to_dict(self) -> dict:
        return asdict(self)
