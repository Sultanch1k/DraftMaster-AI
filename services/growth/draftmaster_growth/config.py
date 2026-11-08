"""Growth-engine configuration (12-factor, environment driven).

Everything is optional. With no environment set at all the agent runs in
``dry_run`` mode against a local JSON state file, which is the intended
behaviour for a fresh clone and for CI.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Canonical links the content engine embeds. Kept in one place so a domain
# change is a one-line edit, not a hunt through templates.
SITE_URL = "https://www.draftmaster.wiki"


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class ChannelConfig:
    """Credentials + enablement for a single publishing channel.

    A channel is only live when it is both enabled and credentialed. Enabling
    without credentials is a configuration mistake, so the adapter downgrades
    itself to dry-run rather than failing the run.
    """

    name: str
    enabled: bool = False
    token: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def live(self) -> bool:
        return self.enabled and bool(self.token.strip())


@dataclass
class GrowthConfig:
    """Runtime configuration for the growth agent."""

    environment: str = "development"
    # State lives outside version control by default; the JSON store is the
    # source of truth and is safe to inspect and diff by hand.
    state_path: str = str(ROOT / "data" / "growth" / "growth-state.json")
    dataset_path: str = str(ROOT / "data" / "artifacts" / "draftmaster-data.json")
    output_dir: str = str(ROOT / "data" / "growth" / "out")

    # Global kill-switch. When False the agent plans and drafts but publishes
    # nothing anywhere, even to channels that are live.
    allow_publish: bool = False

    # The product's own analytics endpoint, used to pull real outcome signal
    # back into the optimizer. Empty disables the feedback loop (the agent then
    # optimizes on internal proxy metrics only).
    metrics_url: str = ""
    metrics_token: str = ""

    # Growth targets. The planner uses these to decide how much to publish.
    posts_per_day: int = 3
    outreach_per_day: int = 5
    videos_per_day: int = 2

    # Exploration rate for the deterministic bandit (0..1). Higher explores more
    # variants; lower exploits the current winner. 0.2 is a sane default for a
    # channel with tens of observations.
    exploration_rate: float = 0.2

    # Channel credentials, one block per channel. Populated from the
    # environment in `from_env`.
    channels: dict[str, ChannelConfig] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "GrowthConfig":
        def chan(name: str, prefix: str) -> ChannelConfig:
            return ChannelConfig(
                name=name,
                enabled=_flag(f"DRAFTMASTER_GROWTH_{prefix}_ENABLED"),
                token=os.environ.get(f"DRAFTMASTER_GROWTH_{prefix}_TOKEN", ""),
            )

        channels = {
            "twitter": chan("twitter", "TWITTER"),
            "reddit": chan("reddit", "REDDIT"),
            "discord": chan("discord", "DISCORD"),
            "telegram": chan("telegram", "TELEGRAM"),
            "blog": ChannelConfig(
                name="blog",
                enabled=_flag("DRAFTMASTER_GROWTH_BLOG_ENABLED", True),
                token="local",  # the blog channel writes files, no credential needed
            ),
        }
        return cls(
            environment=os.environ.get("DRAFTMASTER_GROWTH_ENV", "development"),
            state_path=os.environ.get(
                "DRAFTMASTER_GROWTH_STATE", str(ROOT / "data" / "growth" / "growth-state.json")
            ),
            dataset_path=os.environ.get(
                "DRAFTMASTER_ARTIFACT_PATH", str(ROOT / "data" / "artifacts" / "draftmaster-data.json")
            ),
            output_dir=os.environ.get(
                "DRAFTMASTER_GROWTH_OUTPUT", str(ROOT / "data" / "growth" / "out")
            ),
            allow_publish=_flag("DRAFTMASTER_GROWTH_ALLOW_PUBLISH"),
            metrics_url=os.environ.get("DRAFTMASTER_GROWTH_METRICS_URL", ""),
            metrics_token=os.environ.get("DRAFTMASTER_GROWTH_METRICS_TOKEN", ""),
            posts_per_day=int(os.environ.get("DRAFTMASTER_GROWTH_POSTS_PER_DAY", "3")),
            outreach_per_day=int(os.environ.get("DRAFTMASTER_GROWTH_OUTREACH_PER_DAY", "5")),
            videos_per_day=int(os.environ.get("DRAFTMASTER_GROWTH_VIDEOS_PER_DAY", "2")),
            exploration_rate=float(os.environ.get("DRAFTMASTER_GROWTH_EXPLORATION", "0.2")),
            channels=channels,
        )

    def channel(self, name: str) -> ChannelConfig:
        return self.channels.get(name) or ChannelConfig(name=name)
