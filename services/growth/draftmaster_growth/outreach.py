"""Partner / creator outreach.

The single highest-converting acquisition motion in the growth plan is a
*personalised demo*: a creator's own recent draft, analysed. This module turns
that motion into a repeatable machine:

* a prospect list the agent maintains (seeded from a small built-in list and
  extensible via a JSON file),
* a message generator that produces a genuinely personalised draft analysis for
  the prospect's role/hero, not a form letter,
* a follow-up scheduler that respects a minimum gap between touches so nobody is
  spammed.

Nothing here sends anything unless the outreach channel is live *and* publish is
allowed; otherwise the messages are written to the output directory for review.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import SITE_URL, GrowthConfig
from .models import OutreachMessage, Prospect
from .store import GrowthStore

# A small, honest starter list. Real handles and follower counts are supplied by
# the operator via a JSON file (DRAFTMASTER_GROWTH_PROSPECTS); these are
# placeholders that make the pipeline runnable and demonstrate the shape.
SEED_PROSPECTS: list[dict] = [
    {"key": "creator:mid-lane-lab", "name": "Mid Lane Lab", "platform": "youtube", "followers": 180000, "audience": "mid players, patch guides"},
    {"key": "creator:offlane-academy", "name": "Offlane Academy", "platform": "youtube", "followers": 95000, "audience": "offlane, initiation"},
    {"key": "creator:carry-clinic", "name": "Carry Clinic", "platform": "tiktok", "followers": 120000, "audience": "carry farming, short clips"},
    {"key": "community:ru-dota", "name": "RU Dota Community", "platform": "telegram", "followers": 60000, "audience": "russian-speaking players"},
    {"key": "analyst:stat-line", "name": "Stat Line", "platform": "twitter", "followers": 40000, "audience": "stats, patch analysis"},
]

MIN_DAYS_BETWEEN_TOUCHES = 4


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OutreachEngine:
    """Maintains prospects and generates personalised first-touch messages."""

    def __init__(self, ds, settings: GrowthConfig, store: GrowthStore):
        self.ds = ds
        self.settings = settings
        self.store = store
        self._seed()

    # -- prospect list ---------------------------------------------------
    def _seed(self) -> None:
        for row in SEED_PROSPECTS:
            if not self.store.get_prospect(row["key"]):
                self.store.upsert_prospect(Prospect(**row))
        # Optional operator-supplied list extends/replaces the seed.
        custom = Path(self.settings.output_dir).parent / "prospects.json"
        if custom.exists():
            try:
                for row in json.loads(custom.read_text(encoding="utf-8")):
                    self.store.upsert_prospect(Prospect(**row))
            except (json.JSONDecodeError, TypeError, OSError):
                pass

    def candidates(self, *, limit: int = 5) -> list[Prospect]:
        """Prospects due for a touch: never contacted, or past the cooldown.

        Skips anyone who has replied, won or been marked lost.
        """
        out: list[Prospect] = []
        now = _now()
        for row in self.store.prospects():
            if row.get("status") in {"replied", "won", "lost"}:
                continue
            last = row.get("last_touch") or ""
            if last:
                try:
                    days = (now - datetime.fromisoformat(last)).days
                except ValueError:
                    days = 0
                if days < MIN_DAYS_BETWEEN_TOUCHES:
                    continue
            out.append(Prospect(**{k: v for k, v in row.items() if k in Prospect.__dataclass_fields__}))
        # Deterministic order: most followers first, then key.
        out.sort(key=lambda p: (-p.followers, p.key))
        return out[:limit]

    # -- message generation ---------------------------------------------
    def message(self, prospect: Prospect, locale: str = "en") -> OutreachMessage:
        ds = self.ds
        # Pick a hero that matches the prospect's stated audience, so the demo is
        # about *their* content, not ours.
        hero = self._hero_for(prospect)
        hero_id = hero["id"]
        # The three enemies that hero most often loses to — the actual hook.
        row = ds.counter.get(hero_id, {})
        worst = sorted(
            ((eid, v) for eid, v in row.items() if eid in ds.by_id),
            key=lambda kv: kv[1],
        )[:3]
        enemies = [ds.by_id[eid]["localized_name"] for eid, _ in worst] or ["a standard meta draft"]

        if locale == "ru":
            subject = f"Разбор драфта для {prospect.name}"
            body = (
                f"Привет, {prospect.name}!\n\n"
                f"Мы сделали DraftMaster AI — он превращает вражеский драфт в план на игру, "
                f"а не просто советует героя. Прогнали его на {hero['localized_name']}: "
                f"худшие матчапы — {', '.join(enemies)}.\n\n"
                f"Не пресс-релиз: дайте нам ваш последний драфт, и мы вернём разбор, "
                f"который вы сможете показать зрителям.\n\n"
                f"{SITE_URL}"
            )
        else:
            subject = f"A draft breakdown for {prospect.name}"
            body = (
                f"Hey {prospect.name}!\n\n"
                f"We built DraftMaster AI — it turns an enemy draft into a plan for the game, "
                f"not just a hero suggestion. Ran it on {hero['localized_name']}: "
                f"its worst matchups are {', '.join(enemies)}.\n\n"
                f"Not a press release — send us your last draft and we'll send back a breakdown "
                f"you can put on screen.\n\n"
                f"{SITE_URL}"
            )
        return OutreachMessage(prospect=prospect, subject=subject, body=body, locale=locale)

    def _hero_for(self, prospect: Prospect) -> dict:
        """Pick a hero aligned to the prospect's audience, deterministically."""
        audience = (prospect.audience or "").lower()
        role_map = {
            "mid": ["Nuker", "Escape"],
            "offlane": ["Initiator", "Durable"],
            "carry": ["Carry"],
            "support": ["Support"],
        }
        wanted: list[str] = []
        for keyword, roles in role_map.items():
            if keyword in audience:
                wanted = roles
                break
        pool = [h for h in self.ds.heroes if any(r in h.get("roles", []) for r in wanted)] if wanted else []
        pool = pool or self.ds.heroes
        # Deterministic: the highest-winrate hero in the pool.
        return max(pool, key=lambda h: (h.get("cm_winrate") or 0, -h["id"]))

    # -- actions ---------------------------------------------------------
    def record_touch(self, prospect: Prospect) -> None:
        row = self.store.get_prospect(prospect.key) or prospect.to_dict()
        row["touches"] = int(row.get("touches", 0)) + 1
        row["last_touch"] = _now().isoformat()
        row["status"] = "contacted"
        self.store.upsert_prospect(Prospect(**{k: v for k, v in row.items() if k in Prospect.__dataclass_fields__}))

    def write_messages(self, messages: list[OutreachMessage]) -> list[str]:
        """Persist generated messages for review or sending."""
        out_dir = Path(self.settings.output_dir) / "outreach"
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for m in messages:
            path = out_dir / f"{m.prospect.key.replace(':', '_')}.md"
            path.write_text(
                f"# {m.prospect.name} ({m.prospect.platform})\n\n"
                f"**Subject:** {m.subject}\n\n{m.body}\n",
                encoding="utf-8",
            )
            paths.append(str(path))
        return paths
