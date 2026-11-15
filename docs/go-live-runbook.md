# DraftMaster AI — Go-Live Runbook (turn on revenue)

Follow this once, top to bottom. It takes the product from "cannot take money"
to "a stranger can pay and get premium". Everything here is **free** except the
payment processor's per-sale cut.

Total new recurring cost: **$0**.

---

## 0. Why this is the priority

Verified on the live deployment:

```
$ curl -s https://www.draftmaster.wiki/api/billing/config
{"enabled":false,"checkout_url":"", ...}          <- no way to pay

$ curl -s https://draftmaster-ai.onrender.com/health
{"store_backend":"sqlalchemy","store_detail":"sqlite+pysqlite", ...}  <- data loss on deploy
```

Two independent blockers:

1. **Billing is unconfigured** — the UI correctly hides the buy button, so there
   is no purchase path at all.
2. **The store is SQLite on Render's ephemeral disk.** Per `deployment-runbook.md`
   §4, SQLite "survives a restart but not a redeploy". If a customer pays today,
   the next deploy **silently deletes their entitlement**. They pay, lose
   premium, and ask for a refund.

**Fix both in the same session.** Turning on billing without a durable database
is worse than leaving it off, because it converts a non-sale into a refund and a
bad review.

---

## 1. Durable Postgres — free (Neon)

Render's own free Postgres **expires 30 days after creation** and then becomes
inaccessible — a trap for a paid product. Use Neon instead: genuinely free tier,
no expiry, and it does not spin down.

1. Go to <https://neon.tech> and sign up (free, GitHub login works).
2. Create a project, e.g. `draftmaster`. Pick the region closest to your Render
   service (Render is `frankfurt` per `infra/render.yaml` → choose **AWS
   eu-central-1 / Frankfurt**).
3. Copy the **connection string**. It looks like:

   ```
   postgresql://neondb_owner:XXXXXXXX@ep-xxx-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```

   Use the **pooled** host (it contains `-pooler`). The API normalises
   `postgres://` and `postgresql://` to the psycopg 3 driver automatically, so
   paste it exactly as Neon gives it.

4. That string is the value for `DRAFTMASTER_DATABASE_URL` (step 3 below).

**Cost: $0.** Neon's free tier is far more than this workload needs — the store
holds entitlements, daily quota counters and subscribers, not match data.

> **Alternative if you prefer Supabase** (<https://supabase.com> → free project →
> Settings → Database → Connection string → URI): also $0. Either works; Neon is
> marginally simpler because the pooled connection string is the default.

---

## 2. Lemon Squeezy — payments ($0 fixed)

Lemon Squeezy is the merchant of record: it handles VAT/sales tax and there is
**no monthly fee**, only a per-transaction cut. At this stage that matters more
than a lower headline rate, because it means zero fixed cost and zero tax
paperwork.

### 2.1 Create the account and store

1. Sign up at <https://www.lemonsqueezy.com> and complete the store application
   (your name, business type, payout details). Approval is usually fast.
2. Note the **Store ID** — it is in the URL when you are in the store
   (`.../stores/<STORE_ID>/...`) and under Settings → Stores.

### 2.2 Create the products

Create these as **subscriptions** (Products → New product → Subscription):

| Product | Price | Billing | Notes |
| --- | --- | --- | --- |
| **DraftMaster Premium — Monthly** | $6.99 | monthly | primary |
| **DraftMaster Premium — Annual** | $49.00 | yearly | ~40% off, make this the default in the UI |

For each product, on the product page:

- Enable **License keys** (this is what the app validates). Set the activation
  limit to something small but not 1 — a user switching devices should not be
  locked out. 3 is reasonable.
- Set the **confirmation modal / success message** to tell the buyer: *"Check
  your email for your license key, then paste it into DraftMaster to unlock
  premium."*
- Copy each product's **checkout URL** (the "Share → Checkout link", or
  `https://<store>.lemonsqueezy.com/checkout/buy/<uuid>`).

> The app treats every product as the same `premium` plan and only varies the
> billing period, so no code change is needed to add a second product. The
> monthly checkout URL goes in `DRAFTMASTER_LEMONSQUEEZY_CHECKOUT_URL`.

### 2.3 Get the API key

Settings → API → **Create API key**. Scope it to read products/licenses —
nothing more. This is `DRAFTMASTER_LEMONSQUEEZY_API_KEY`.

### 2.4 Configure the webhook

This keeps entitlements honest after the sale: a cancellation, expiry or refund
must revoke premium even if the user never returns.

1. Settings → Webhooks → **Add webhook**.
2. **URL:** `https://draftmaster-ai.onrender.com/api/billing/webhook`
3. **Signing secret:** generate one, e.g.
   `python -c "import secrets;print(secrets.token_urlsafe(32))"`
   → this is `DRAFTMASTER_LEMONSQUEEZY_WEBHOOK_SECRET`.
4. Subscribe to at least: `subscription_cancelled`, `subscription_expired`,
   `subscription_paused`, `order_refunded`.

### 2.5 Legal pages

Lemon Squeezy will not approve a store without reachable policies. The app now
ships `/privacy`, `/terms` and `/refund` (added in this change). Point Lemon
Squeezy at:

- Privacy: `https://www.draftmaster.wiki/privacy`
- Terms: `https://www.draftmaster.wiki/terms`
- Refunds: `https://www.draftmaster.wiki/refund`

Fill in a real support address in those pages (see step 3,
`DRAFTMASTER_SUPPORT_EMAIL`) before submitting.

---

## 3. Set the environment variables

### API (Render → `draftmaster-api` → Environment)

| Variable | Value | Why |
| --- | --- | --- |
| `DRAFTMASTER_ENVIRONMENT` | `production` | enables the durability guard |
| `DRAFTMASTER_DATABASE_URL` | Neon connection string (§1) | **durable entitlements** |
| `DRAFTMASTER_SECRET_KEY` | `python -c "import secrets;print(secrets.token_urlsafe(48))"` | signs premium tokens; **changing it logs everyone out** |
| `DRAFTMASTER_LEMONSQUEEZY_API_KEY` | §2.3 | license validation |
| `DRAFTMASTER_LEMONSQUEEZY_STORE_ID` | §2.1 | license validation |
| `DRAFTMASTER_LEMONSQUEEZY_CHECKOUT_URL` | §2.2 monthly checkout URL | the Upgrade button target |
| `DRAFTMASTER_LEMONSQUEEZY_WEBHOOK_SECRET` | §2.4 | HMAC for the webhook |
| `DRAFTMASTER_SUPPORT_EMAIL` | your address | shown in the upgrade panel |
| `DRAFTMASTER_CORS_ORIGINS` | `https://www.draftmaster.wiki` | lock CORS down |

Billing turns on only when `API_KEY` **and** `STORE_ID` **and** `SECRET_KEY` are
all present. Save → Render redeploys.

### Web (Vercel → `draft-master-ai` → Settings → Environment Variables)

| Variable | Value |
| --- | --- |
| `API_PROXY_TARGET` | `https://draftmaster-ai.onrender.com` |
| `NEXT_PUBLIC_SITE_URL` | `https://www.draftmaster.wiki` |

---

## 4. Verify — the go/no-go check

Run the preflight script; it checks every revenue-critical invariant and exits
non-zero if anything is wrong:

```bash
python scripts/preflight.py --api https://draftmaster-ai.onrender.com
```

Expected all-green:

```
[ok]   api reachable, environment=production
[ok]   store is durable (postgresql+psycopg)      <- NOT sqlite/memory
[ok]   billing enabled
[ok]   checkout url present
[ok]   forged license key rejected
[ok]   flagship report returns all sections
```

Then a **real end-to-end purchase test** (do this once, then refund yourself —
Lemon Squeezy test mode can also be used):

1. Open the site, run 3 analyses, hit the paywall on the 4th.
2. Click Upgrade → complete a real (or test-mode) purchase.
3. Paste the license key → confirm premium unlocks and the daily limit lifts.
4. Confirm the payment appears in Lemon Squeezy and the customer row exists:

   ```bash
   curl -s -H "x-metrics-token: $DRAFTMASTER_SECRET_KEY" \
     https://draftmaster-ai.onrender.com/api/metrics
   # "paying_customers": 1
   ```

5. **Redeploy the API** and confirm the customer is *still* premium. This is the
   test that proves blocker #2 is actually fixed. Do not skip it.

---

## 5. If something fails

| Symptom | Cause | Fix |
| --- | --- | --- |
| `/health` shows `sqlite+pysqlite` | `DRAFTMASTER_DATABASE_URL` unset or wrong | re-paste the Neon pooled URL; redeploy |
| `/health` shows `memory` | driver could not load the URL | check the scheme; the app rewrites `postgres://`, do not hand-edit |
| `enabled:false` in billing config | one of api key / store id / secret key missing | set all three on Render |
| Webhook returns 401 | signing secret mismatch | regenerate and re-paste both sides |
| License key rejected | product has license keys disabled, or key belongs to a different store | enable license keys on the product |
| Premium disappears after a deploy | the store was not durable when they bought | fix §1, then re-activate from their license key |

---

## 6. What this unlocks

After §4 passes, the product can take money. The remaining work is **demand**,
not capability: getting strangers to the site and to the paywall. That is
`docs/revenue-plan.md` §4, steps 4–7 — share loop, communities, email, creators.
All of it is free; none of it works until this runbook is done.
