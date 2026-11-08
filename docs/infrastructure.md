# DraftMaster AI — Infrastructure

## 1. Topology

```
                    ┌──────────────────────────────────────┐
   Users ─────────► │  Vercel Edge / CDN                    │
                    │  apps/web (Next.js 16)                │
                    │  · static assets cached at the edge   │
                    │  · /api/* rewritten to the backend    │
                    └────────────────┬─────────────────────┘
                                     │ HTTPS
                    ┌────────────────▼─────────────────────┐
                    │  API host (Render / any container)    │
                    │  FastAPI + uvicorn (2+ workers)       │
                    │  · dataset loaded once per worker     │
                    │  · engine runs in-process             │
                    └───────┬───────────────────┬──────────┘
                            │                   │
              ┌─────────────▼──────┐  ┌─────────▼─────────────┐
              │  Postgres          │  │  Redis                │
              │  profiles, usage,  │  │  analysis + match     │
              │  analyses, billing │  │  caches, rate limits  │
              └────────────────────┘  └───────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  Object storage│   artifacts (future)
                    └────────────────┘
```

## 2. Why these choices

| Decision | Rationale |
| --- | --- |
| **Next.js on Vercel** | First-class CDN, instant previews, server-side proxy removes CORS entirely |
| **FastAPI** | Native async, Pydantic validation that doubles as the OpenAPI contract, trivial container image |
| **Engine as a package** | The compute has no framework dependency, so it is testable in isolation and relocatable later |
| **Postgres** | Relational integrity for billing, JSONB for report history, `gen_random_uuid()` and `CITEXT` without extensions |
| **Redis** | Sub-millisecond cache reads for the hot path and a shared rate-limit counter |
| **Artifacts as files** | 1.1 MB JSON loads in milliseconds and deploys atomically with the code — no database round trip on boot |

## 3. Graceful degradation

The platform is designed so that **every external dependency is optional**:

| Missing | Behaviour |
| --- | --- |
| Redis | In-memory cache; logs `cache backend=memory` |
| Postgres | SQLite in `data/`; logs `store backend=sqlalchemy` |
| OpenDota key | Anonymous requests at a lower rate limit |
| Valve CDN | UI falls back to initials; detection uses precomputed hashes |

This is why a fresh clone runs with no configuration, and why a managed-service
outage degrades rather than fails.

## 4. Container image

`infra/Dockerfile` builds a two-stage Python image:

1. Builder installs `requirements.txt` into a virtualenv.
2. Runtime copies only the venv, the service code and the artifacts.

The image is small (no build toolchain in the final layer), runs as a non-root user,
and starts uvicorn with a health check on `/health`.

## 5. Environment variables

| Variable | Required | Notes |
| --- | --- | --- |
| `DRAFTMASTER_DATABASE_URL` | prod | `postgresql+psycopg://…` |
| `DRAFTMASTER_REDIS_URL` | prod | `redis://…` |
| `DRAFTMASTER_OPENDOTA_API_KEY` | recommended | Higher OpenDota limits |
| `DRAFTMASTER_ENVIRONMENT` | recommended | `production` |
| `DRAFTMASTER_CORS_ORIGINS` | recommended | Comma-separated allowlist in prod |
| `API_PROXY_TARGET` | frontend | Backend URL for the Next.js rewrite |

## 6. Observability

- **Logs** — structured `key=value` lines from `logging.basicConfig`; each request
  logs its path, status and latency via uvicorn's access log.
- **Health** — `/health` returns dataset size, patch and generation timestamp, so a
  stale artifact is visible at a glance.
- **Metrics (planned)** — request rate, p50/p95 latency, quota rejections, cache hit
  ratio, screenshot detection confidence distribution, and win-probability
  calibration (predicted vs observed win rate).
- **Errors (planned)** — Sentry on both the API and the web app, with release
  tagging tied to the deploy.

The single most important production metric is **calibration**: of the games where
the engine predicted a 60% win, did the user actually win ~60%? Every other metric is
secondary to that.

## 7. CI/CD

`infra/ci.yml` defines the pipeline:

1. **Python** — install, run the full test suite (engine, API, screenshot).
2. **Web** — install, `tsc --noEmit`, `next build`.
3. **Artifacts** — validate that the committed artifacts load and contain 127 heroes.
4. **Deploy** — on `main`: web to Vercel, API to Render (`infra/render.yaml`).

Preview deploys are created per pull request. Because the dataset is committed, a
preview is fully functional without any pipeline run.

## 8. Cost model (early stage)

| Component | Provider | Rough monthly cost |
| --- | --- | --- |
| Web | Vercel Pro | $20 |
| API | Render Starter | $7 |
| Postgres | Render Basic (paid) | $6 |
| Redis | Upstash (serverless) | $0–10 |
| Domain + email | — | ~$15 |
| **Total** | | **~$40–80/month** |

This comfortably supports the first tens of thousands of users, because analysis is
CPU-trivial and the dataset is tiny. Revenue does not need to scale with
infrastructure until analytics workloads appear in Phase 2.

## 9. Backup and recovery

- Postgres: daily automated snapshots, 7-day retention, point-in-time recovery.
- Artifacts: committed to git, so any version is reproducible from the repository.
- Redis: treated as pure cache; no backup required.
- Recovery objective: RPO 24 h, RTO < 1 h. Restoring is a redeploy plus a snapshot
  restore, because no critical state lives outside Postgres.
