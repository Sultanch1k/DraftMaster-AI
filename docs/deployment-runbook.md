# DraftMaster AI — Deployment Runbook

How to ship, verify and roll back production. Written for the person on call at
2 a.m., not for a design review.

## 1. What runs where

| Piece | Host | Production branch / root | Notes |
| --- | --- | --- | --- |
| Web (`apps/web`, Next.js 16) | Vercel | branch **`main`**, root dir `apps/web` | `www.draftmaster.wiki` is aliased here |
| API (`services/api`, FastAPI) | Render | auto-deploys from **`main`** | `draftmaster-ai.onrender.com` |
| Postgres | Render | — | injected as `DRAFTMASTER_DATABASE_URL` |
| Dataset artifact | in the image | — | `data/artifacts/draftmaster-data.json`, 1.1 MB |

The API is reached only through the web app: `next.config.mjs` rewrites
`/api/:path*` to `API_PROXY_TARGET`. `/health` is **not** under `/api`, so it is
not proxied — hit the Render host directly to inspect it.

> `import-implementation` is the repo's default branch and Vercel builds it, but
> that build is **not** promoted to the production alias. Merging to `main` is
> what changes the live site.

## 2. Release

`main` is protected by CI (`.github/workflows/ci.yml` runs on pushes to `main`
and `import-implementation`). To release:

```bash
git push origin import-implementation        # CI runs here first
gh api repos/Sultanch1k/DraftMaster-AI/merges \
  -X POST -f base=main -f head=import-implementation \
  -f commit_message="Release: <what changed>"
```

Vercel redeploys the web app and Render redeploys the API from the same merge.
Both are automatic; there is nothing to click.

## 3. Required environment variables

Backend (Render → draftmaster-api → Environment):

| Variable | Purpose |
| --- | --- |
| `DRAFTMASTER_ENVIRONMENT` | must be `production` |
| `DRAFTMASTER_DATABASE_URL` | managed Postgres; **see §4 — never leave this unset** |
| `DRAFTMASTER_SECRET_KEY` | signs premium session tokens; changing it logs everyone out |
| `DRAFTMASTER_CORS_ORIGINS` | `https://www.draftmaster.wiki` |
| `DRAFTMASTER_OPENDOTA_API_KEY` | match coach + meta intelligence |
| `DRAFTMASTER_LEMONSQUEEZY_API_KEY` | license validation |
| `DRAFTMASTER_LEMONSQUEEZY_STORE_ID` | license validation |
| `DRAFTMASTER_LEMONSQUEEZY_CHECKOUT_URL` | the Upgrade button target |
| `DRAFTMASTER_LEMONSQUEEZY_WEBHOOK_SECRET` | HMAC for `/api/billing/webhook` |
| `DRAFTMASTER_SUPPORT_EMAIL` | shown in the upgrade panel |

Frontend (Vercel → draft-master-ai → Settings → Environment Variables):

| Variable | Purpose |
| --- | --- |
| `API_PROXY_TARGET` | backend origin, e.g. `https://draftmaster-ai.onrender.com` |

Billing stays hidden until `api_key` **and** `store_id` **and** `secret_key` are
all set — `/api/billing/config` returns `enabled: false` until then, and the UI
hides purchase affordances rather than showing a dead button.

`infra/render.yaml` is the Blueprint that provisions the API service and a paid
Postgres. Apply it with Render → New → Blueprint. It sets `autoDeploy: true`.

## 4. The data-durability rule (read this before touching the DB)

Render injects its Postgres connection string with the `postgres://` scheme,
which SQLAlchemy cannot load. `normalize_database_url()` in
`services/api/draftmaster_api/infra.py` rewrites `postgres://` and
`postgresql://` to `postgresql+psycopg://`. Without it the store falls back to
in-memory, and every entitlement, quota counter and subscriber is lost on the
next restart.

The trap is the middle ground: **a SQLite file on Render's ephemeral disk is not
durable either** — it survives a restart but not a redeploy, which is worse
because it looks fine until a deploy silently wipes paying customers.

`/health` reports `store_backend` and `store_detail` so this is verifiable from
outside, without a secret:

```bash
curl -s https://draftmaster-ai.onrender.com/health
# ... "store_backend":"sqlalchemy","store_detail":"postgresql+psycopg"   <- correct
# ... "store_detail":"sqlite+pysqlite"                                   <- data loss on deploy
# ... "store_backend":"memory"                                           <- data loss on restart
```

Startup logs an `ERROR` when `DRAFTMASTER_ENVIRONMENT=production` and the store
is not durable. Treat that line as a release blocker.

**Use a paid Postgres.** Render's free Postgres is a trap for a paid product:
"Free Render Postgres databases expire 30 days after creation" and "An expired
Free database is inaccessible unless you upgrade it to a paid compute plan"
([Render docs — Free](https://render.com/docs/free)). A month after launch every
customer's premium would vanish, with a 14-day grace period to notice.

## 5. Post-deploy verification

Run all of these; each has a known-good answer.

```bash
# 1. API is up and the store is durable (see §4 for the expected values)
curl -s https://draftmaster-ai.onrender.com/health

# 2. Billing surface answers
curl -s https://draftmaster-ai.onrender.com/api/billing/config

# 3. A forged token must NOT grant premium
curl -s -X POST https://draftmaster-ai.onrender.com/api/billing/activate \
  -H 'Content-Type: application/json' \
  -d '{"license_key":"DM-FORGED-AAAA-BBBB"}' -o /dev/null -w '%{http_code}\n'   # expect 422

# 4. The flagship engine returns all 11 sections for EVERY recommended hero
curl -s -X POST https://draftmaster-ai.onrender.com/api/analyse \
  -H 'Content-Type: application/json' \
  -d '{"enemy_hero_ids":[19,2,27],"role":"carry","rank_tier":80}' \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['report']; \
print(len(r['pick_reports']), 'reports;', 'one_sentence' in r)"

# 5. The web app is live and SEO pages render (no literal {hero})
curl -s https://www.draftmaster.wiki/robots.txt
curl -s https://www.draftmaster.wiki/counter/anti-mage | grep -c 'does best'
```

## 6. Rollback

Both hosts deploy per commit, so roll back by reverting the merge on `main`:

```bash
git revert -m 1 <merge_sha>      # or revert the individual commit
git push origin main
```

Vercel and Render both redeploy automatically. If the API is broken but the web
app is fine, use Render's "Rollback" on the service to restore the previous
build without touching git.

## 7. Incident: customers lost premium

Symptom: users report premium disappeared, usually right after a deploy.

1. Check `/health` → `store_detail`. `sqlite+pysqlite` or `memory` confirms the
   cause.
2. Set `DRAFTMASTER_DATABASE_URL` to the managed Postgres connection string.
3. Restore the latest Postgres backup if the data was previously in Postgres
   (Render → database → Backups).
4. Re-activate affected customers from their Lemon Squeezy license keys, or
   verify against the provider; entitlements are keyed by email.
5. Post-mortem: why did the deploy not fail? The startup `ERROR` log in §4
   exists to make this loud.
