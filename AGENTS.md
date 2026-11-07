# AGENTS.md — repository guide for AI agents

DraftMaster AI is a Dota 2 draft-strategy platform. It turns an enemy draft into a
complete win plan. Read this before making changes.

## Mental model

The product is a **statistical engine with a UI on top**, not a chatbot. The rule that
shapes every decision: *the strategy engine must stay deterministic, testable and
reproducible.* The same draft must always produce the same report. Language models may
narrate numbers the engine produced; they must never invent them.

## Layout

| Path | What lives here |
| --- | --- |
| `services/engine/draftmaster_engine/` | Pure-Python strategy engine. No web framework imports, ever. |
| `services/api/draftmaster_api/` | FastAPI surface: routers, schemas, config, infra adapters. |
| `apps/web/src/` | Next.js 15 App Router frontend. |
| `tools/pipeline/` | Builds the data artifacts from OpenDota + Valve's CDN. |
| `data/artifacts/` | Committed build outputs — the engine's only data dependency. |
| `docs/` | Product, architecture, roadmap and risk documentation. |

## Commands

```bash
# Backend (from repo root, venv at .venv)
cd services/api && ../../.venv/bin/python -m uvicorn draftmaster_api.main:app --port 12001

# Frontend
cd apps/web && API_PROXY_TARGET=http://127.0.0.1:12001 npm run dev -- --port 12000

# Tests (always run before claiming a change works)
.venv/bin/python -m pytest services/engine/tests -q

# Typecheck + production build
cd apps/web && npx tsc --noEmit && npm run build
```

## Conventions

- **Python:** type hints everywhere, `from __future__ import annotations`, dataclasses
  for value objects, pure functions in the engine. Imports at the top of the file.
- **Engine purity:** `draftmaster_engine` must never import FastAPI, SQLAlchemy or
  anything request-scoped. It takes a `Dataset` and returns dataclasses.
- **Degradation:** every external dependency (Redis, Postgres, OpenDota, Valve CDN)
  must be optional, with a working fallback. A fresh clone runs with zero config.
- **Frontend:** types in `src/lib/types.ts` mirror the Pydantic schemas by hand; keep
  them in sync. Tailwind tokens and component classes live in `tailwind.config.ts` and
  `globals.css` — reuse `.card`, `.chip`, `.btn-*` rather than inventing new styles.
- **Comments:** explain *why*, never restate the code or narrate the diff.

## Testing expectations

- Engine behaviour → `services/engine/tests/test_engine.py`.
- API contracts and quota → `tests/test_api.py`.
- Screenshot detection → `tests/test_screenshot.py`. This test downloads **real hero
  portraits** from Valve's CDN and composites them; it is deliberately not mocked.
  Prefer real inputs over fixtures whenever the point of the test is accuracy.
- Do not weaken an assertion to make a test pass. If a test encodes a contract that
  genuinely changed, update the test and say why.

## Gotchas discovered so far

- `strong_against` / `countered_by` in `best_picks` are **lists of hero names**
  (strings), not objects. The frontend types must match or `ReportView` crashes.
- The API mounts some routes outside `/api` (`/`, `/health`, `/api/heroes`); the
  flagship list on `/` is asserted by substring in tests.
- Screenshot detection is gated by **both** a confidence floor and a runner-up
  margin. Loosening the floor alone causes false positives.
- Postgres needs `psycopg[binary]` in `services/api/requirements.txt`. Without it the
  store silently falls back to memory in production — it now logs a warning instead.
- `DRAFTMASTER_` prefixes every setting; `API_PROXY_TARGET` configures the Next.js
  rewrite to the backend.
- Docker image runs as a non-root user, so `chmod -R a+rX` runs over the copied code;
  the engine is on `PYTHONPATH` at `/app/services/engine`.

## Definition of done

1. Tests pass (`pytest`), types check (`tsc --noEmit`), and the production build
   succeeds (`next build`).
2. The feature works in the browser, not just in a unit test.
3. Docs updated when behaviour, config or contracts change.
