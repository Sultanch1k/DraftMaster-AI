# DraftMaster AI

**The Dota 2 AI coach that tells you how to win the game — not just which hero to pick.**

Every other tool stops at "pick hero X". DraftMaster AI turns the enemy draft into a
complete, actionable win plan in under five seconds: the best hero, the exact item
build, the items to avoid, kill priority, power spikes, match timeline and win
conditions — computed from real OpenDota match statistics, not a static guide.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Enemy draft: Lion · Axe · Shadow Shaman                             │
├──────────────────────────────────────────────────────────────────────┤
│  ONE-SENTENCE WIN PLAN                                               │
│  "If you get Black King Bar on time, kill Axe first, avoid enemy     │
│   initiations until BKB is up, this match is heavily favoured        │
│   (72% draft win probability)."                                      │
│                                                                      │
│  #1 BEST PICK   Lone Druid       WIN PROBABILITY   71.7% vs 28.3%    │
│  KEY COUNTERS   BKB · Aeon Disk · Heart of Tarrasque                 │
│  KILL ORDER     Axe → Lion → Shadow Shaman                           │
│  PRIMARY WC     Kill Axe first in every fight; convert Roshan → T1   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Table of contents

- [Why this is not another counter picker](#why-this-is-not-another-counter-picker)
- [Feature set](#feature-set)
- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Data pipeline](#data-pipeline)
- [How the engine works](#how-the-engine-works)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Licence & attribution](#licence--attribution)

---

## Why this is not another counter picker

| Typical tool | DraftMaster AI |
| --- | --- |
| "Pick Slark." | "Pick Slark, buy Diffusal by 14:00, never take a fight before BKB, and kill Sniper first." |
| Static, hand-written builds | Item build generated per enemy draft from live item-popularity data, with a written reason for every item |
| Win-rate tables | A **WIN PROBABILITY ENGINE** that decomposes a draft edge into percentage points and compresses it by rank |
| One screen of advice | An 11-section report plus a one-screen panic mode for use *during* the draft |
| Manual input only | Upload a draft screenshot — heroes are detected from pixels and analysed automatically |
| No accountability | Match-ID coach grades your real game against bracket benchmarks and gives a practice plan |

The product thesis: **draft advantage is real, measurable and convertible.**
DraftMaster AI measures it, explains it, and hands the player a plan to convert it.

## Feature set

### Flagship — ONE CLICK WIN PLAN™
One button, one screen, sub-5-second answer. Best hero, full build, danger heroes,
power spikes, kill priority, win condition, items to avoid, and a single-sentence
win plan.

### 🚨 PANIC MODE — "I'M LAST PICK"
The viral surface. During a live draft, a player has seconds. Panic Mode returns
only the decision plus its reasoning: `#1 hero`, `full build`, `danger heroes`,
`power spikes`, `kill priority`, `win condition`, `items to avoid`,
`one-sentence win plan`.

### Draft report (11 sections)
1. **Best picks** — `#1–#5` with Counter / Meta / Comfort / Synergy / Difficulty /
   Lane / Role / Final scores, each explained.
2. **Why this hero works** — human-readable reasoning, never a raw number.
3. **Complete threat analysis** — magic, physical, pure, burst, sustain, crowd
   control, teamfight, pickoff, push, split-push, Roshan, early/mid/late.
4. **Dynamic item builder** — starting → lane → early → mid → late → luxury →
   situational → emergency → *items to avoid*, each with a reason.
5. **Skill build** — level 1–30 progression with alternatives and adaptation cases.
6. **Talent tree** — every tier, recommended option, alternative and reason.
7. **Match plan** — 0-10 / 10-20 / 20-30 / 30-45 / 45+ with objectives, farm focus,
   fight focus, map movement, tower priority, Roshan priority and danger zones.
8. **Win conditions** — primary, secondary and emergency.
9. **Target priority** — ranked kill order with a reason per enemy.
10. **Power spike engine** — hero level, item, draft, teamfight and objective spikes
    for both sides.
11. **One-sentence win plan** — the take-away.

### Advanced features
- **Screenshot analyzer** — a two-stage perceptual detector (dHash + aHash + colour
  histogram, coarse scan → pixel-level refinement with a confidence margin) detects
  the heroes in a draft screenshot and feeds them straight into the engine.
- **Match-ID coach** — pulls a real match from OpenDota and grades farm, XP, last
  hits, fighting and survival against bracket benchmarks, then gives a practice plan.
- **Personal AI coach** — stored profile (role, rank, favourite heroes, comfort,
  playstyle) that re-weights every recommendation.
- **Comfort pick engine** — `Final = 40% counter · 20% meta · 20% comfort ·
  10% synergy · 10% role`, tunable per user.
- **Meta intelligence** — trending heroes, patch winners and patch losers from live
  Captain's Mode and public pick data.
- **WIN PROBABILITY ENGINE™** — draft win probability with a full attribution of
  which factors moved the number and by how many percentage points.

### Monetisation
- **Free** — 3 analyses per day.
- **Premium** — unlimited analyses, match coaching, AI coach, patch reports,
  advanced strategy analysis.

## Architecture

```
                       ┌───────────────────────────────────────────┐
   Browser (mobile      │  Next.js 15 · React 19 · TypeScript        │
   first, dark theme)   │  Tailwind · Shadcn-style primitives        │
                       │  /api/* proxied through the Next server    │
                       └───────────────────────┬───────────────────┘
                                               │  same-origin /api
                       ┌───────────────────────▼───────────────────┐
                       │  FastAPI (draftmaster_api)                 │
                       │  routers: analysis · coach · reference ·   │
                       │           screenshot                       │
                       │  infra: Cache (Redis→memory) ·             │
                       │         Store (Postgres→SQLite→memory)     │
                       └───────────────────────┬───────────────────┘
                                               │  in-process
                       ┌───────────────────────▼───────────────────┐
                       │  draftmaster_engine                        │
                       │  dataset · scoring · threats · items ·     │
                       │  plan · winprob · report · coach ·         │
                       │  screenshot                                │
                       └───────────────────────┬───────────────────┘
                                               │  loads once at boot
                       ┌───────────────────────▼───────────────────┐
                       │  data/artifacts/draftmaster-data.json      │
                       │  data/artifacts/hero-hashes.json           │
                       │  ← built by tools/pipeline (OpenDota)      │
                       └───────────────────────────────────────────┘
```

The engine is a pure Python package with no framework dependency, so it can run
in-process (as here), as a separate service, or inside a batch job. The API layer
degrades gracefully: with no `REDIS_URL` it uses an in-memory cache, and with no
`DATABASE_URL` it uses SQLite — so the whole platform runs with zero external
services and scales by setting two environment variables.

## Repository layout

```
.
├── apps/
│   └── web/                         # Next.js 15 frontend
│       └── src/
│           ├── app/                 # layout, page, global styles, icon
│           ├── components/          # UI components (see docs/ui-component-map.md)
│           └── lib/                 # api client, types, formatting
├── services/
│   ├── api/                         # FastAPI backend
│   │   ├── draftmaster_api/
│   │   │   ├── main.py              # app factory + lifespan
│   │   │   ├── config.py            # 12-factor settings
│   │   │   ├── infra.py             # cache + store adapters
│   │   │   ├── schemas.py           # pydantic request/response models
│   │   │   └── routers/             # analysis, coach, reference, screenshot
│   │   └── requirements.txt
│   └── engine/                      # pure-Python strategy engine
│       ├── draftmaster_engine/
│       │   ├── dataset.py           # artifact loading + counter-matrix access
│       │   ├── scoring.py           # pick scoring (counter/meta/comfort/…)
│       │   ├── threats.py           # 14-dimension threat analysis
│       │   ├── items.py             # dynamic item builder
│       │   ├── plan.py              # skill build, talents, match plan, targets
│       │   ├── winprob.py           # WIN PROBABILITY ENGINE
│       │   ├── report.py            # report orchestration
│       │   ├── coach.py             # OpenDota match coach
│       │   └── screenshot.py        # hero detection
│       ├── tests/                   # 58 tests (engine, API, real-image detection)
│       └── setup.py
├── tools/
│   └── pipeline/
│       ├── build_datasets.py        # OpenDota → draftmaster-data.json
│       └── build_hero_hashes.py     # hero portraits → hero-hashes.json
├── data/
│   ├── artifacts/                   # committed build outputs
│   └── raw/                         # raw OpenDota cache (gitignored)
├── docs/                            # product, architecture, roadmaps, risks
├── infra/                           # Docker, Railway, CI
└── requirements.txt
```

## Quickstart

Requirements: Python 3.11+ and Node 20+.

```bash
# 1. Backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e services/engine
cd services/api && uvicorn draftmaster_api.main:app --reload --port 12001

# 2. Frontend (new terminal)
cd apps/web
npm install
API_PROXY_TARGET=http://127.0.0.1:12001 npm run dev -- --port 12000
```

Open <http://localhost:12000>. The dataset artifacts are committed, so no pipeline
run is needed to start.

Rebuild the data (optional, needs network access to OpenDota and Valve's CDN):

```bash
python tools/pipeline/build_datasets.py      # heroes, items, counters, talents
python tools/pipeline/build_hero_hashes.py   # portrait signatures for screenshot detection
```

## Configuration

All settings are environment variables prefixed `DRAFTMASTER_` (see
`services/api/draftmaster_api/config.py`).

| Variable | Default | Purpose |
| --- | --- | --- |
| `DRAFTMASTER_ENVIRONMENT` | `development` | Environment name surfaced by `/health` |
| `DRAFTMASTER_DATABASE_URL` | SQLite in `data/` | Postgres in production |
| `DRAFTMASTER_REDIS_URL` | *(empty)* | Redis cache; falls back to in-memory |
| `DRAFTMASTER_OPENDOTA_API_KEY` | *(empty)* | Higher OpenDota rate limits |
| `DRAFTMASTER_FREE_DAILY_ANALYSES` | `3` | Free-plan quota |
| `DRAFTMASTER_CACHE_TTL_SECONDS` | `300` | Analysis cache TTL |
| `DRAFTMASTER_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `API_PROXY_TARGET` | `http://127.0.0.1:12001` | Next.js → FastAPI proxy target |

## API reference

Base URL `/api`. Interactive docs at `/docs` when the API is running.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Service metadata + flagship endpoints |
| `GET` | `/health` | Status, hero count, patch, dataset timestamp |
| `GET` | `/api/heroes` | Full hero list with roles and icons |
| `GET` | `/api/heroes/{id}` | Single hero |
| `GET` | `/api/heroes/{id}/matchups` | Best/worst matchups from the counter matrix |
| `GET` | `/api/items` | Item index |
| `GET` | `/api/meta` | Trending heroes, patch winners, patch losers |
| `POST` | `/api/analyse` | Full 11-section report |
| `POST` | `/api/panic` | Panic Mode one-screen answer |
| `POST` | `/api/win-probability` | WIN PROBABILITY ENGINE only |
| `POST` | `/api/screenshot/analyse` | Multipart image → detected heroes → report |
| `POST` | `/api/match/coach` | Match-ID coaching report (OpenDota) |
| `GET` | `/api/match/{id}` | Match summary |
| `GET` | `/api/profile/{user_id}` | Read stored profile |
| `PUT` | `/api/profile` | Upsert profile |

Example:

```bash
curl -s http://127.0.0.1:12001/api/panic \
  -H 'content-type: application/json' \
  -d '{"enemy_hero_ids":[26,2,27],"role":"carry","rank_tier":70}' | jq .
```

Requests accept `x-user-id` (profile + quota key) and `authorization: Bearer
premium-token` (premium plan) headers.

## Data pipeline

`tools/pipeline/build_datasets.py` pulls from OpenDota and Valve's CDN and emits a
single self-describing artifact (`data/artifacts/draftmaster-data.json`):

- **Heroes** — names, roles, attributes, portraits, public win/pick rates and
  Captain's-Mode win rates.
- **Ability meta** — per-hero damage type, crowd control, disable and nuke counts,
  used by the threat engine.
- **Counter matrix** — pairwise matchup advantage, computed from real
  head-to-head results and **empirically shrunk** toward neutral to remove
  small-sample noise.
- **Item popularity** — per-hero, per-phase purchase rates (starting, lane, early,
  mid, late), which is what makes the item builder dynamic rather than static.
- **Duration curves** — win rate by game length, powering power spikes and the
  win-probability engine's game-clock factor.
- **Talents** — every tier with resolved bonus placeholders.

`tools/pipeline/build_hero_hashes.py` downloads each portrait and stores a dHash, an
aHash and a 4×4×4 RGB histogram. The screenshot detector computes the same
signatures on candidate tiles, which is why detection is real image recognition
rather than filename matching.

## How the engine works

- **Counter matrix** (`dataset.py`) — shrunk log-odds pairwise advantage. Shrinking
  is what stops a hero with 40 games and a lucky streak from topping the list.
- **Pick scoring** (`scoring.py`) — `Final = 40% counter · 20% meta · 20% comfort ·
  10% synergy · 10% role`, with difficulty and lane-matchup scores shown separately.
- **Threats** (`threats.py`) — 14 dimensions with per-dimension danger levels.
- **Items** (`items.py`) — filters to finished items, strips components, dedupes,
  and mixes meta-popular items with **counter items derived from the enemy draft**,
  attaching a written reason to each.
- **Win probability** (`winprob.py`) — starts at 50% and adds attributed
  contributions (hero matchups, meta strength, threat mismatch, game clock, role
  fit), then compresses toward 50% by rank, because lower-MMR players convert draft
  edges less reliably.
- **Screenshot** (`screenshot.py`) — coarse grid scan → pixel-level refinement →
  confidence floor *and* runner-up margin, which is what turns "best guess per tile"
  into a precise detector.

## Testing

```bash
python -m pytest services/engine/tests -q
```

- `test_engine.py` — engine behaviour, invariants and known matchups.
- `test_api.py` — API integration against an isolated SQLite DB and in-memory cache.
- `test_screenshot.py` — **real-image** detection: genuine hero portraits are
  downloaded from Valve's CDN, composited into a draft row, and the detector must
  recover them. Nothing is mocked.

## Deployment

- **Frontend** → Vercel (`apps/web`). Set `API_PROXY_TARGET` to the backend URL.
- **Backend** → Railway / Fly / any container host (`infra/Dockerfile`). Set
  `DRAFTMASTER_DATABASE_URL` and `DRAFTMASTER_REDIS_URL` for production.
- **Postgres + Redis** → managed instances; the app auto-creates its tables on boot.

See `docs/infrastructure.md` for the full topology and `infra/` for ready-to-use
configs.

## Documentation

| Document | Contents |
| --- | --- |
| `docs/product-spec.md` | Vision, personas, full feature specification, UX flows |
| `docs/architecture.md` | System design, data model, request lifecycle |
| `docs/database-schema.md` | Tables, indexes, retention and analytics schema |
| `docs/api-design.md` | Endpoint contracts and error model |
| `docs/ui-component-map.md` | Component tree, wireframes and design tokens |
| `docs/roadmap.md` | MVP roadmap and scaling roadmap |
| `docs/infrastructure.md` | Deployment topology, caching, observability |
| `docs/ai-strategy.md` | Where AI adds value, and where it must not |
| `docs/monetization.md` | Pricing, revenue roadmap, unit economics |
| `docs/competitive-analysis.md` | Competitors and defensibility |
| `docs/risks.md` | Technical and product risks with mitigations |
| `docs/growth.md` | Growth and launch strategy |

## Licence & attribution

Data © OpenDota and Valve Corporation. DraftMaster AI is an independent project and
is not affiliated with Valve Corporation. Dota 2 and all hero imagery are trademarks
and copyright of Valve Corporation.
