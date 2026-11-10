# DraftMaster AI — Revenue-First Plan

> Goal: the **first genuine paying customer** acquired through a repeatable,
> measurable, economically sensible process — at the lowest possible cash outlay.
> Everything below is judged against one question: *does this get us a paying
> customer sooner?*

This plan is written from a verified audit of the live product, not from the
aspirational docs. Where a claim is unverified it says so.

---

## 1. What is actually true today

| Thing | Status | Evidence |
| --- | --- | --- |
| Product works end-to-end | ✅ | live `POST /api/panic` returns a full plan in ~4 ms |
| Paywall (3 free/day → 402) | ✅ | verified locally: 3 distinct drafts OK, 4th → 402 |
| Billing code (Lemon Squeezy, HMAC, webhook) | ✅ built + tested | 6 billing tests pass |
| **Billing configured in production** | ❌ **`enabled:false`, `checkout_url:""`** | live `/api/billing/config` |
| Durable datastore in production | ✅ | live `/api/metrics` → `store_backend: sqlalchemy` |
| Funnel analytics (first-party) | ✅ | events endpoint + private metrics endpoint |
| SEO counter pages | ✅ | 128 URLs in `sitemap.xml` |
| Legal / trust pages (privacy, terms, refunds) | ❌ 404 | needed to sell |
| Share / referral loop | ❌ none | no `navigator.share` anywhere |
| Growth content links resolve | ❌ `/meta`, `/panic`, `/hero/*` → 404 | only `/counter/*` exists |

**The single blocking fact: there is no way to take money right now.** The app
hides the buy button because billing is unconfigured. Until that changes, no
amount of traffic, SEO or content can produce revenue. This is priority zero.

---

## 2. Cost structure — why this can reach profit on ~$0 marginal spend

The engine is pure CPU over a 1.1 MB artifact; an analysis costs ~$0.005 of
direct cost and completes in single-digit milliseconds. That means:

- **Cost of goods is effectively zero.** Margin is >99% before fixed costs.
- **The only real cost is a handful of fixed subscriptions**, all of which have a
  free tier sufficient for the first customers:

| Need | Paid option | **Free option (recommended)** | Cost |
| --- | --- | --- | --- |
| API + web hosting | Vercel Pro $20/mo | Vercel **Hobby** (already deployed) | $0 |
| Postgres (entitlements, quotas, subs) | Render $7/mo | **Neon** or **Supabase** free tier | $0 |
| Redis (cache) | Upstash $10/mo | in-memory cache is fine at this scale; or Upstash free tier | $0 |
| Payments | Stripe $0/mo | **Lemon Squeezy** — no monthly fee, % per sale, merchant-of-record (handles VAT) | $0 fixed |
| Email | Mailchimp/ConvertKit $ | **SMTP** (Gmail/Brevo free tier) + own sender | $0 |
| Analytics | PostHog $ | already built first-party | $0 |
| Domain | — | already owned | sunk |

**Target fixed monthly burn: $0.** Revenue is therefore profit from the first
sale. The correct decision at this stage is to run entirely on free tiers and
only upgrade when a limit is actually hit (e.g. Neon's storage cap, Vercel's
bandwidth cap) — each of which is triggered by *success*, not by setup.

---

## 3. Ranked opportunity list

Ranked by (expected revenue impact ÷ cost ÷ time), with honest probability.

| # | Opportunity | Impact | Cost | Time | P(success) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Turn billing on** (Lemon Squeezy + checkout URL + secret) | Blocking | $0 | ~1 h setup | 95% | **Do now** |
| 2 | **Legal pages** (privacy, terms, refund) | Unblocks selling + trust | $0 | 2 h | 95% | **Do now** |
| 3 | **Viral share loop** (share win plan + OG image) | High | $0 | 4 h | 70% | **Do now** |
| 4 | **Niche community seeding** (r/Dota2, r/learndota2, Discords) | High | $0 | ongoing | 50% | **Do after 1–2** |
| 5 | **SEO** — fix dead links, add free `/last-pick` tool page | Medium (compounds) | $0 | 4 h | 60% | **Do now** |
| 6 | **Email nurture** (installable sender) | Medium | $0 | 4 h | 55% | Do |
| 7 | **Creator partnerships** (small/medium channels) | High | $0–low | ongoing | 40% | Prepare, then pitch |
| 8 | **Product-led growth** (free tool → account → paywall) | High | $0 | structural | 60% | Inherent in 1–6 |
| 9 | **Referral program** (give a week, get a week) | Medium | revenue share | 6 h | 35% | After first 10 customers |
| 10 | **Affiliate** | Low early | rev share | 8 h | 25% | Later |
| 11 | **Paid ads** | — | cash | — | 10% | **Do not** — burns capital before retention is proven |
| 12 | **Team/API tiers** | — | — | — | — | **Do not** — wrong stage |

Two things I am deliberately recommending against: paid ads and new paid
infrastructure. Both spend money to hide the real question — *does the free user
convert at all?* — which is unanswered until billing is on.

---

## 4. The fastest path to the first paying customer

A concrete sequence. Steps 1–3 are the critical path; 4–7 run in parallel and
compound.

**Step 1 — Turn on billing (the only true blocker).**
Create a Lemon Squeezy store + two products (Premium monthly $6.99, annual $49),
set the four env vars on the API host, and the checkout URL. Done when
`/api/billing/config` returns `enabled:true` and a real purchase mints a working
license key. *See `docs/go-live-runbook.md`.*

**Step 2 — Legal pages.** Lemon Squeezy (as merchant of record) requires a
reachable privacy policy, terms and refund policy before approval. Add three
static pages. Cheap, and it also raises buyer trust.

**Step 3 — Instrument and confirm the funnel fires.** With billing on, a user
must be able to go: land → draft → paywall (4th analysis) → checkout → license
key → activated. Verify each event lands in `/api/metrics`.

**Step 4 — Share loop.** One tap shares the win plan; the shared link renders a
dynamic OG image showing the draft and the win probability. This is the only
free distribution channel that compounds *inside* the product, and Dota players
share wins compulsively.

**Step 5 — Seed the niche communities.** Honest, value-first posts to
r/learndota2, r/Dota2, and the big Dota Discords, plus a Show HN / Product Hunt
launch. Drafts prepared in `docs/launch-kit.md`, published only with approval.

**Step 6 — Email the list.** The paywall already captures emails with consent.
A single honest "patch X is live, here's what changed" send re-activates the
warmest leads.

**Step 7 — Creator outreach.** Small/medium Dota channels have high trust and
cheap reach. Offer an affiliate cut rather than an upfront fee — it costs
nothing until it works.

**Definition of done for the milestone:** one non-refunded payment from a
stranger, attributable to a channel we can repeat.

---

## 5. Pricing recommendation

Current design: Free (3/day), Premium **$6.99/mo** or **$49/yr**.

My recommendation: **keep $6.99 monthly, but make the annual plan the default
and add a low-friction entry point.**

Reasoning:
- $6.99 is below Dota Plus (~$4/mo) + one cosmetic, and well under a single
  paid coaching session. For a committed ranked player (30–60 games/month) it is
  <$0.25/game for a possible win-rate edge. The value case is strong.
- The **real risk is not price, it is first-purchase hesitation** — a stranger
  paying a new site with no track record. Two changes reduce that friction
  without cutting the price:
  1. **A weekly plan (~$1.99)** captures "I want one weekend of ranked." It is
     the smallest possible first yes, and the easiest to repeat.
  2. **Annual default** in the UI converts cash up front and cuts churn.
- **Do not discount the monthly plan yet.** There is no evidence price is the
  barrier; discounting before measuring trains users to wait for a sale.

**Pricing is a hypothesis, not a fact.** The experiments in §6 test it.

---

## 6. Experiment backlog

Each experiment has a hypothesis, a cost, a measurement, and a decision rule.
Priority order; only one runs at a time.

| ID | Hypothesis | Cost | Measure | Decision rule |
| --- | --- | --- | --- | --- |
| E1 | A visible share button raises acquisition | $0 | `share_clicked` → new sessions | keep if >3% of reports shared |
| E2 | Legal pages lift checkout completion | $0 | paywall → checkout → activated | keep if completion rises |
| E3 | A free `/last-pick` page ranks and converts | $0 | organic sessions → `analysis_run` | keep if any organic signups |
| E4 | Weekly $1.99 raises first-purchase rate | $0 | checkout starts by plan | adopt if weekly >25% of starts |
| E5 | Annual default lifts revenue/subscriber | $0 | plan mix | adopt if ARPU up, refunds flat |
| E6 | 5/day free limit beats 3/day | $0 | D7 retention vs conversion | keep the higher revenue/day |
| E7 | Community posts beat SEO for early signups | $0 | signups by `source` | double down on the winner |

**Stop rule:** a channel that produces zero paying customers after ~2 weeks of
real effort is paused, not nursed. Time is the scarcest resource here.

---

## 7. Financial model (honest, not a projection)

Fixed monthly burn at the recommended setup: **$0.**

| Paying customers | MRR @ $6.99 | Monthly cost | **Operating profit** |
| --- | --- | --- | --- |
| 1 | $6.99 | ~$0 (+ ~2.9%+30¢ fees) | **positive (~$6.50)** |
| 10 | $69.90 | ~$0 | **positive (~$67)** |
| 100 | $699 | maybe $20 (Neon/Vercel upgrade) | **positive (~$660)** |

**Profitability is not the hard part — the near-zero cost base guarantees it
almost immediately. The hard part is the first sale, and then retention.**

What actually decides success:
- **Conversion at the paywall.** The only number that matters early. 3/day free,
  and the 4th analysis lands mid-session at peak intent — a good design, but
  unproven. Target: 2–4% of engaged users.
- **Retention.** A tool that doesn't visibly help gets cancelled in ~2 months.
  Accuracy and calibration are revenue work, not polish.
- **Churn is the ceiling.** At $6.99, LTV ≈ $6.99 ÷ monthly churn. To justify
  even $20/mo of infrastructure you need enough subscribers that churn doesn't
  erase them — which is why staying on free tiers until *forced* off is correct.

**What would make me say this fails:** if, after real traffic, the paywall
conversion is under ~1% and share rate is under ~1%, the demand thesis is wrong
and the honest move is to change the offer (or the audience) — not to spend on
ads.

---

## 8. What I need from you (approvals & resources)

I will do all of the above myself. These are the points that need **your**
action, because they involve money, your identity, or public publishing:

1. **Lemon Squeezy account + store** (free to create; % per sale, no monthly fee).
   Sign up at <https://www.lemonsqueezy.com>, create the store, add the two
   products, then give me the API key, store ID, checkout URL and webhook secret
   via the host's env vars. **No recurring cost.** Full steps in
   `docs/go-live-runbook.md`.
2. **Neon (or Supabase) Postgres** — free tier, for durable entitlements.
   <https://neon.tech> → create project → copy the connection string into
   `DRAFTMASTER_DATABASE_URL`. **Free.**
3. **Approval to publish** the community/creator drafts in
   `docs/launch-kit.md` under your brand.
4. **A support/refund email address** to show in the UI and give the payment
   provider.

Nothing here requires spending money. Everything else — code, pages, share
loop, SEO, email sender, analytics — I can build and test without you.

---

## 9. Sequencing summary

```
NOW (blocking)     billing on  →  legal pages  →  verify funnel
PARALLEL ($0)      share loop  ·  fix SEO links + /last-pick  ·  email sender
THEN               seed communities  →  email the list  →  creator outreach
MEASURE            paywall conversion, share rate, signups by source
DECIDE             double down on the winning channel; pause the rest
MILESTONE          first paying customer, repeatably
```

The plan is intentionally small. The product is already built and fast; the
missing piece is a live payment path and a reason for strangers to arrive. Fix
those two things, measure, and let the numbers decide the next move.
