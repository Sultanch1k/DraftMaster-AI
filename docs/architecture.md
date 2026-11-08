# DraftMaster AI — System Architecture

## 1. Overview

DraftMaster AI is a monorepo with three deployable units and one build-time tool:

| Unit | Technology | Responsibility |
| --- | --- | --- |
| `apps/web` | Next.js 16 / React 19 / TypeScript / Tailwind | All user-facing UI; proxies `/api/*` to the backend |
| `services/api` | FastAPI / Pydantic v2 / SQLAlchemy | HTTP surface, auth, quota, caching, persistence |
| `services/engine` | Pure Python (numpy, Pillow, httpx) | All strategy computation and image detection |
| `tools/pipeline` | Python | Builds the data artifacts from OpenDota + Valve's CDN |

The split exists for one reason: **the engine must be testable and reusable without
a web framework.** It is a plain package with a single `ReportEngine` façade, which
means it can run in-process (today), as a standalone microservice (later), or inside
an offline batch job (dataset validation), with no code changes.

## 2. Layering

```
┌───────────────────────────────────────────────────────────────┐
│ Presentation         apps/web (React Server + Client)         │
│   · pages, components, api client, types                      │
├───────────────────────────────────────────────────────────────┤
│ Transport            services/api (FastAPI)                   │
│   · routers · schemas · config · quota · auth headers         │
├───────────────────────────────────────────────────────────────┤
│ Infra adapters       services/api/infra.py                    │
│   · Cache  (Redis → in-memory)                                │
│   · Store  (Postgres → SQLite → memory)                       │
├───────────────────────────────────────────────────────────────┤
│ Domain               services/engine/draftmaster_engine       │
│   · dataset · scoring · threats · items · plan · winprob      │
│   · report · coach · screenshot                               │
├───────────────────────────────────────────────────────────────┤
│ Data                 data/artifacts/*.json                    │
│   · draftmaster-data.json (heroes, counters, items, talents)  │
│   · hero-hashes.json (portrait signatures)                    │
└───────────────────────────────────────────────────────────────┘
```

Dependencies point strictly downwards. The engine never imports FastAPI; the API
never imports React; the pipeline never imports the engine.

## 3. Request lifecycle — `POST /api/panic`

1. **FastAPI** validates the body against `PanicRequest` (1–5 hero ids, role, rank).
2. `_validate_ids` rejects unknown hero ids with `422`.
3. `_enforce_quota` charges the user's daily counter in `Store` once per distinct
   draft (locale-independent signature); re-requests of the same draft are free and
   free users over the limit receive a localized `402` with an explicit upgrade
   message.
4. `ReportEngine` computes the draft summary, best hero, win probability, item
   build, target priority, power spikes and win conditions — all pure functions over
   the in-memory dataset.
5. The response is serialised, returned, and (for `/api/analyse`) written to `Cache`
   keyed by a hash of the request.

Everything after step 3 is CPU-only and completes in single-digit milliseconds,
which is why Panic Mode comfortably meets its sub-5-second end-to-end budget.

## 4. Data model (artifacts)

`draftmaster-data.json` is the single source of truth for the engine:

```
{
  "generated_at": ISO8601,
  "source": "opendota",
  "patch": { "name", "date", "id" },
  "heroes": [
    { "id", "name", "localized_name", "roles", "primary_attr", "attack_type",
      "icon", "img", "tags", "capabilities": { magic, physical, pure, cc,
      "bkbpierce_cc", "nuke_count", "disable_count", "silence", "stun" },
      "pub_winrate", "pub_pick", "cm_winrate",
      "item_timings": { starting|lane|early|mid|late: [ {key, count} ] },
      "winrate_by_duration": [ {minute, winrate} ],
      "talents": [ {level, options} ] }
  ],
  "items": { "<key>": { dname, cost, img, created, components, finished } },
  "counter_matrix": { "<attacker>": { "<victim>": logit } }
}
```

`hero-hashes.json` holds the portrait signatures used by the screenshot detector:
per hero a 64-bit dHash, a 64-bit aHash and a 64-entry quantised RGB histogram.

Both artifacts are committed so a fresh clone runs with no pipeline step.

## 5. Engine internals

| Module | Responsibility | Key idea |
| --- | --- | --- |
| `dataset.py` | Load the artifact, expose `by_id`, `counter`, `counter_logit` | Shrunk log-odds accessor with a neutral default |
| `scoring.py` | Score every hero for a draft | Weighted blend; returns eight sub-scores plus reasons |
| `threats.py` | 14-dimension threat analysis | Per-dimension aggregation with danger thresholds |
| `items.py` | Dynamic item build | Meta popularity **mixed with draft-derived counter items** |
| `plan.py` | Skill build, talents, match plan, target priority, win conditions | Rule-based, threat-aware, with adaptation notes |
| `winprob.py` | WIN PROBABILITY ENGINE | Attributed percentage-point contributions, rank-compressed |
| `report.py` | Orchestration | Assembles the 11 sections into one response |
| `coach.py` | OpenDota match coach | Isolated HTTP client + benchmark grading |
| `screenshot.py` | Hero detection | Two-stage perceptual matching with a margin gate |

### 5.1 Why the counter matrix is shrunk

Raw head-to-head win rates are noisy: a hero with 60 games and a lucky streak can
outrank a genuinely strong counter with 50,000 games. The pipeline therefore
estimates each pairwise advantage and shrinks it toward neutral in proportion to the
sample size:

```
advantage_shrunk = advantage_raw * n / (n + k)
```

where `n` is the observed sample and `k` a smoothing constant. This is what makes the
recommendations stable and defensible, and it is the main statistical differentiator
versus competitors who publish raw win-rate tables.

### 5.2 Why the win probability is attributed

A bare "58%" is unfalsifiable and unlearnable. The engine starts from a 50% baseline
and adds named contributions — hero matchups, meta strength, threat mismatch, game
clock, role fit — then applies an execution-reliability factor for the player's rank,
because draft edges convert less reliably at lower MMR. The user sees each term and
its magnitude in percentage points.

## 6. Frontend architecture

- **Next.js App Router.** A single page with a client-side tab shell (`lastpick`,
  `draft`, `screenshot`, `coach`, `meta`) so switching views never refetches.
- **Server-side proxy.** `next.config.mjs` rewrites `/api/:path*` to
  `API_PROXY_TARGET`. The browser therefore talks to exactly one origin: no CORS
  configuration, no exposed backend port, and it works behind any tunnel.
- **Types mirror the API.** `src/lib/types.ts` is a hand-maintained mirror of the
  Pydantic schemas; `tsc --noEmit` is part of the build gate.
- **Rendering.** Hero portraits are plain `<img>` tags with an initials fallback, so
  a CDN outage degrades gracefully instead of breaking layout.
- **Design tokens.** Tailwind theme extension defines the dark palette (`base`,
  `radiant`, `dire`, `gold`, `magic`) and reusable component classes (`.card`,
  `.chip`, `.btn-*`, `.label`).

## 7. Caching

| Layer | Key | TTL | Backend |
| --- | --- | --- | --- |
| Analysis | hash(enemy ids, hero, role, rank, comfort) | 300 s | Redis → memory |
| Match coach | `match:{id}:{account}` | 600 s | Redis → memory |
| Dataset | process memory | process lifetime | loaded once at boot |
| Portraits | browser HTTP cache | Valve CDN | CDN |

## 8. Scaling path

1. **Vertical (today).** One process serves both API and engine; the dataset is
   ~1.1 MB and analysis is CPU-cheap. This comfortably handles thousands of
   requests per second.
2. **Horizontal API.** The API is stateless apart from cache and store, both of which
   are externalised by setting `DRAFTMASTER_REDIS_URL` and
   `DRAFTMASTER_DATABASE_URL`. Add replicas behind a load balancer.
3. **Engine extraction.** Because the engine has no framework dependency it can be
   moved behind its own service or into a worker pool for expensive batch jobs.
4. **Dataset serving.** When artifacts outgrow memory, move them to object storage
   with an in-process LRU, keeping the `Dataset` interface unchanged.
5. **Read replicas.** Analytics and meta reports move to a Postgres read replica,
   leaving the hot path on the primary.

## 9. Failure modes and mitigations

| Failure | Impact | Mitigation |
| --- | --- | --- |
| OpenDota unavailable | Match coach fails | Isolated client, `502` with a clear message, cached responses still served; the draft engine is unaffected |
| Valve CDN unavailable | Portraits missing | Initials fallback in the UI; hashes are precomputed, so detection still works |
| Redis unavailable | No shared cache | Automatic in-memory fallback; the service never fails to start |
| Postgres unavailable | No persistence | SQLite fallback; profiles and quotas keep working |
| Corrupt artifact | Engine cannot boot | Fail fast at startup with an explicit log line; artifacts are validated by the test suite |
| Screenshot unreadable | Upload fails | `422` with an actionable message; manual selection remains available |
