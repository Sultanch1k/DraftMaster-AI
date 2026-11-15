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
| `services/growth/draftmaster_growth/` | Autonomous growth agent: content, outreach, publishing, self-improvement. |
| `apps/web/src/` | Next.js 16 App Router frontend (next-intl, cookie-based locale). |
| `tools/pipeline/` | Builds the data artifacts from OpenDota + Valve's CDN. |
| `data/artifacts/` | Committed build outputs — the engine's only data dependency. |
| `data/growth/` | Growth-agent state (tracked) + generated output (gitignored). |
| `docs/` | Product, architecture, roadmap and risk documentation. |

## Commands

```bash
# Backend (from repo root, venv at .venv)
cd services/api && ../../.venv/bin/python -m uvicorn draftmaster_api.main:app --port 12001

# Frontend
cd apps/web && API_PROXY_TARGET=http://127.0.0.1:12001 npm run dev -- --port 12000

# Tests (always run before claiming a change works)
.venv/bin/python -m pytest services/engine/tests -q
.venv/bin/python -m pytest services/growth/tests -q

# Growth agent (dry run by default; --live required to publish)
.venv/bin/python -m draftmaster_growth plan
.venv/bin/python -m draftmaster_growth run

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
- **Next.js must stay on the latest patched release.** Vercel refuses to deploy a
  build whose Next.js version has an open advisory ("Vulnerable version of Next.js
  detected"). Bump `apps/web/package.json` (`next`, `react`, `react-dom`, `next-intl`)
  and re-run `npm audit` before pushing; keep the Docker/CI Node version at ≥20.9
  (Next 16 requires it). CI now runs `npm audit --audit-level=high` in the web job, so
  a vulnerable bump fails the pipeline before it reaches Vercel.
- **Vercel's production branch is `main`.** The custom domain `draftmaster.wiki`
  (→ `www.draftmaster.wiki`) is attached to the `draft-master-ai` project with root
  directory `apps/web`. `import-implementation` is the repo default branch, and a push
  to it does trigger a Vercel deployment, but that deployment is **not** promoted to the
  production alias: the site only changes after the commit reaches `main` (observed
  2026-11-08 — pushing the monetization commit to `import-implementation` left
  `/counter/*` at 404 until it was merged into `main`). Release by merging into `main`.
  If the domain ever returns `x-vercel-error: DEPLOYMENT_NOT_FOUND`, it means the
  aliased deployment is missing or failed — not a DNS problem. Deployments are
  preview-protected (SSO); automation can reach a preview with the
  `x-vercel-protection-bypass` header, but that secret is header/query-only and does
  not apply to client-side XHRs.
- **The API is hosted on Render, not Railway.** The Next.js rewrite forwards `/api/*`
  to it (responses carry `x-render-origin-server: uvicorn`). Render injects its
  Postgres connection string as `postgres://…`, which SQLAlchemy cannot load; without
  `normalize_database_url` (in `infra.py`) the store falls back to in-memory and every
  entitlement, quota counter and subscriber is lost on the next restart. Verify
  durability from outside with `/health` → `store_backend`; `"memory"` in production is
  a data-loss bug, not a benign fallback. `store_detail` narrows it further: only
  `postgresql+psycopg` is durable — `sqlite+pysqlite` survives a restart but not a
  redeploy. `docs/deployment-runbook.md` has the release, verify and rollback steps.
- `DRAFTMASTER_` prefixes every setting; `API_PROXY_TARGET` configures the Next.js
  rewrite to the backend.
- Docker image runs as a non-root user, so `chmod -R a+rX` runs over the copied code;
  the engine is on `PYTHONPATH` at `/app/services/engine`.
- **`why_this_hero` follows the *requested* hero, not the top pick.** `best_picks`
  always stays the ranked Top-5; an explicit `hero_id` drives sections 2–11 (why, item
  build, skill build, talents, match plan, win conditions, kill priority, spikes). When
  `hero_id` is omitted the #1 pick is used.
- **Localization is a boundary concern.** `draftmaster_engine/i18n.py` maps the engine's
  deterministic English prose to Russian by pattern; the engine core stays locale-free.
  The API translates response bodies (`locale.py`) and the locale is part of the Redis
  cache key — EN and RU reports for one draft must never share an entry. Hero names,
  item names and all numbers are never translated. **Every** prose-bearing endpoint is
  locale-aware: `/analyse`, `/panic`, `/win-probability`, `/threat-analysis`, `/meta`
  and `/match/coach`. Adding a new endpoint that returns prose means wiring
  `resolve_locale(request)` + `localize(...)`, or the Russian UI will leak English.
- **next-intl:** the locale lives in the `draftmaster_locale` cookie (no `[locale]`
  route segment). `useTranslations('<namespace>')` is required per namespace — calling
  `t('fields.x')` inside the `report` namespace throws `MISSING_MESSAGE` at render time,
  which Next.js only surfaces as an error overlay, not a build failure.
- **A missing placeholder is not an error in next-intl — it renders `{hero}` to the
  user.** That shipped on all 127 `/counter/*` pages (`t('itemsSub')` with no values
  against a string containing `{hero}`) and nobody saw it for a patch. `npm run build`
  now runs `apps/web/scripts/check-i18n-placeholders.mjs` first, which resolves every
  `t('key')` against the namespace bound by the nearest `useTranslations`/
  `getTranslations` in the file and fails the build on an unfulfilled placeholder. Run
  `npm run check:i18n` after editing `messages/*.json`. EN and RU are at exact parity
  (255 keys, matching placeholders) — keep them that way.
- **React keys must not mix id spaces.** The five enemy-draft slots render either a hero
  (`key={`hero-${id}`}`) or an empty placeholder (`key={`slot-${i}`}`). Using the raw
  hero id and the raw slot index in the same list collides whenever a selected hero's
  id equals a placeholder index (e.g. Axe is id `2`), which React reports as a duplicate
  key. This only appears in the dev overlay — the production build stays silent — so
  always check the browser console, not just `npm run build`, after touching such lists.
- **Quota is per distinct draft, not per HTTP call.** `_enforce_quota` hashes the draft
  and options (locale excluded) and charges each signature once per day, cached under a
  `quota:<user>:<day>:<signature>` marker. Re-requesting the same draft — the language
  switch re-fetches the report in the new locale — is free. Tests must therefore use
  *distinct* drafts to exercise the limit, and the frontend refreshes the last analysis
  on a locale change via `lastRunRef`.
- **The header quota bar reads one `usage` state.** Every paid action (Panic, full
  report, screenshot) returns `usage` and the page stores it in a single `setUsage`
  call, so the counter stays correct regardless of which feature was used. Do not
  read usage off a single result object (e.g. `panic?.usage`) — that silently misses
  the full-report and screenshot paths.
- **`DraftReport.to_dict()` returns a shallow copy**, not the live `__dict__`. The
  manual-pick branch stores a pick's dict inside `pick_reports`; returning `__dict__`
  made that dict contain itself and broke JSON serialization ("Circular reference").
- **`pick_reports` ships a full 11-section report for every Top-5 pick** so clicking a
  recommended hero is instant and never spends quota. Keep the key set in sync with
  `best_picks` (keys are `str(hero_id)`).
- **The growth agent is deterministic and dry by default.** `draftmaster_growth` never
  calls `random`; the bandit explores on a rotation keyed to observation count, and the
  topic ring advances by a counter — so `plan` twice and diff to check a change. A channel
  is live only when it is enabled *and* credentialed *and* `DRAFTMASTER_GROWTH_ALLOW_PUBLISH`
  is set; otherwise every adapter records a dry run. It reuses `draftmaster_engine`'s
  `Dataset`, so a growth post can never contain a number the product would not produce.
  Dedupe keys off `ContentItem.signature` (topic + data + locale), **not** `topic` — using
  the key alone made English and Russian collide and re-published the same subject. Tests
  live in `services/growth/tests/`; `data/growth/out/` is gitignored while the state file is
  tracked so the scheduled workflow can persist it. See `docs/growth-agent.md`.

- **The match plan must stay draft-specific.** `plan._phase_content()` takes `threats`
  and `delta`; it used to accept and ignore both, so every draft produced an identical
  5-phase timeline — the exact "static guide" behaviour the product claims to replace.
  When you touch it, keep the threat-driven notes wired and keep
  `test_match_plan_adapts_to_enemy_draft` passing: it asserts two different enemy drafts
  yield different plans for the same hero, and it fails if the timeline goes static again.

- **Production store is NOT durable yet.** `/health` on `draftmaster-ai.onrender.com`
  reports `sqlite+pysqlite`. The Render service was created by hand, so `infra/render.yaml`
  (which provisions a paid Postgres) never applied — a Blueprint only manages services it
  created. Setting `DRAFTMASTER_DATABASE_URL` on the existing service fixes it; see
  `docs/go-live-runbook.md` §1. `scripts/preflight.py` fails on `[store is durable]` until
  then, which is the intended go/no-go gate. Do not enable billing before it passes:
  a paying customer whose entitlement is wiped on the next deploy is worse than no sale.

- **The free quota charges per distinct analysis, keyed by user + IP.** Same draft twice is
  free; three *distinct* drafts then a 402. To exercise the paywall locally, send three
  different `enemy_hero_ids` — repeating one draft returns 200 forever and looks like the
  limit is broken.

- **Branch topology — and the production split-brain it causes.** `main` is the
  branch that production deploys from: Vercel aliases `www.draftmaster.wiki` to a
  `main` build (per `docs/deployment-runbook.md` §1). `import-implementation` is
  the default branch where work lands, and Vercel builds it as a **preview only** —
  merging to `main` is what changes the live site. The API on Render has drifted
  from this: it serves `import-implementation` directly (proven — production
  returns a `plan.py` string introduced on `import-implementation` that has never
  existed on `main`). So the two hosts can disagree: a fix can be live in the API
  while the web app that calls it is a release behind. Before claiming anything is
  "in production", check *both* hosts, and remember a 404 on `www.draftmaster.wiki`
  usually means "unreleased", not "broken". Release with the documented command in
  `docs/deployment-runbook.md` §2 (merge `import-implementation` → `main`).

## Definition of done

1. Tests pass (`pytest`), types check (`tsc --noEmit`), and the production build
   succeeds (`next build`).
2. The feature works in the browser, not just in a unit test.
3. Docs updated when behaviour, config or contracts change.
