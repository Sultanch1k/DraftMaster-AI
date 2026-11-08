# DraftMaster AI — Roadmap

## MVP (shipped in this repository)

Everything below is implemented, tested and running.

| # | Deliverable | Status |
| --- | --- | --- |
| 1 | OpenDota data pipeline → `draftmaster-data.json` | ✅ 127 heroes, 501 items, patch 7.41 |
| 2 | Shrunk counter matrix from real head-to-head results | ✅ |
| 3 | Threat engine (14 dimensions) | ✅ |
| 4 | Dynamic item builder with reasons and avoid-list | ✅ |
| 5 | Skill build 1–30, talents, match plan, win conditions, target priority, power spikes | ✅ |
| 6 | WIN PROBABILITY ENGINE with attributed factors | ✅ |
| 7 | FastAPI backend with quota, cache and persistence | ✅ |
| 8 | Next.js frontend: Panic Mode + 11-section report + screenshot + coach + meta | ✅ |
| 9 | Screenshot hero detection (real-image tested) | ✅ 5/5 at 91–99% |
| 10 | Match-ID coach on live OpenDota data | ✅ |
| 11 | Test suite | ✅ 58 passed / 1 skipped |
| 12 | Docs, README, deployment configs | ✅ |

## Phase 1 — Public beta (weeks 1–4)

**Goal:** prove retention with real ranked players.

- Real authentication (Steam OpenID + email magic link).
- Stripe subscriptions with a real paywall and entitlement check.
- Analysis history and a personal dashboard.
- Persist every analysis to Postgres; start the meta feedback loop.
- Sentry + structured logging + uptime checks.
- Shareable Panic Mode images (auto-rendered PNG) — the primary viral loop.

**Exit criteria:** 1,000 activated users, D7 ≥ 30%, ≥ 50 paying subscribers.

## Phase 2 — Depth and trust (weeks 5–12)

**Goal:** become the most *accurate* tool, measurably.

- **Outcome feedback loop.** Record the user's actual match result after each
  recommendation and recalibrate the win-probability engine against reality. This is
  the single most valuable data asset the product can own.
- **Draft-order awareness.** Account for pick phase (first pick, last pick, bans) in
  recommendations, not just the final enemy lineup.
- **Ally-aware scoring.** Synergy currently uses a neutral default; replace it with a
  real pairwise synergy matrix derived from the same match data.
- **Hero mastery tracking** from public match history via OpenDota, feeding the
  comfort engine automatically.
- **Patch automation.** A scheduled job rebuilds artifacts on each patch and diffs
  the recommendations, producing an automatic patch report.
- **Coaching depth.** Replay-level lane analysis (last-hit curves, death clustering,
  objective timings) rather than end-of-match aggregates.

**Exit criteria:** measured recommendation accuracy published as a public backtest.

## Phase 3 — Platform (months 4–9)

- **Live draft mode.** Overwolf/GSI integration that watches the pick screen and
  updates Panic Mode automatically — no manual selection.
- **Five-stack captain mode.** Multi-seat drafting with ban suggestions and
  role-assignment optimisation.
- **Public API and embeds.** A paid API and an embeddable widget for streamers and
  community sites.
- **Team accounts.** Shared profiles, scrim history, opponent scouting.
- **Native mobile apps.** React Native shells around the same API.

## Phase 4 — Beyond Dota (months 10+)

The engine is game-agnostic in structure: a shrunk pairwise matrix, a capability
model, a dynamic item builder and an attributed probability engine. Deadlock, League
of Legends and mobile MOBAs are all addressable by replacing the data pipeline and
the capability mapping — the architecture does not change.

## Scaling roadmap

| Stage | Users | Architecture |
| --- | --- | --- |
| Local | 1 | Single process, SQLite, in-memory cache |
| Launch | ≤ 10k | API replicas + managed Postgres + Redis |
| Growth | ≤ 250k | Read replicas, CDN-cached reference data, engine worker pool |
| Scale | ≤ 2M | Multi-region API, sharded analytics, artifact object storage + LRU |

The dataset is ~1.1 MB and analysis is CPU-cheap, so the hot path stays in-process
for a long time. The first true scaling pressure will be analytics, not analysis —
which is why the analytics schema is designed for aggregation from day one.

## Explicitly deferred

Live in-game overlays with real-time advice, automated draft bots, tournament
scrim tooling, and any feature that would require reading game memory or injecting
into the client. DraftMaster AI advises before and after the game; it does not touch
the game process.
