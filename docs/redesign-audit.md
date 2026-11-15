# Visible Redesign + Share Loop — Audit and Delivery

This document records what was claimed versus what was actually live, why the
"premium redesign" and "friend sharing" were not visible on the live site, and
what this change delivers to close the gap.

## 1. What was claimed vs. what was live

| Area | Claimed | Actually live (before this change) |
| --- | --- | --- |
| Homepage | "Premium Win Plan design system, Hero Identity + Tactical Editorial" | A generic SaaS dashboard: a `card card-pad` hero block, a tab bar, and a hero grid. The redesign had landed only at the **token level** (`globals.css`, `tailwind.config.ts`, ~23 lines in `page.tsx`) — the *composition* never changed. |
| Sharing | "Share win plan", social posters, OG cards | A small ghost button in the Win Plan header plus a poster panel buried in the footer. Not a first-class action, and in production it was entirely dead (see below). |
| Production API | Deployed | **Stale.** Render had not redeployed despite `autoDeploy: true`; `/api/panic` returned the old response shape and newer endpoints 404'd. |
| Share loop | Works | **Dead in production.** `POST /api/share` returned `{"token":"","path":"","win_probability":77.0}` — an empty token — because `DRAFTMASTER_SECRET_KEY` was never set on Render. No signing key means no share link, no poster, no OG card. |

The root cause of the visible gap: the earlier work was real but **invisible at
the composition layer**. Design tokens and a handful of component-level edits do
not change what a visitor sees. The homepage still opened with a card, and the
share action still looked like an afterthought.

## 2. What this change delivers

### 2.1 The homepage is now composed, not just re-tokenised

- `components/home/HomeHero.tsx` — a cinematic opening band: a montage of six
  hero artworks under a heavy scrim, an editorial serif headline, and the two
  analysis modes presented as first-class, equal-weight choices. This is the
  first thing a visitor sees and it no longer looks like a dashboard.
- `components/home/ActionBar.tsx` — the command bar sits directly under the hero
  grid. The five enemy slots fill in as the user picks, and the two flagship
  actions ("I'M LAST PICK" and "One Click Win Plan™") are always one thumb away.
- `components/home/HowItWorks.tsx` — a four-step editorial strip that states the
  promise (a game plan, not a hero pick) before any interaction.
- `ModeChooser` was removed; the modes are now inline and always visible, so
  there is no hidden modal standing between a newcomer and the product.

### 2.2 Sharing is a first-class experience

- `components/ShareWithFriends.tsx` — a prominent, accent-bordered panel at the
  top of every Win Plan: **Copy link**, **Share** (native share sheet), and
  **Poster** (three formats). It reports what happened for every action.
- Sharing now works in **both** modes. "My Hero" shares are supported end to end:
  the mode is baked into the signed token (`m: "strategy"`), and
  `GET /api/share/{token}` rebuilds the matching plan. The poster and OG card
  render either mode through a single normalized view model.
- `ShareView` and the share-page metadata now distinguish a counter-pick share
  ("… — DraftMaster AI win plan") from a My Hero share ("… — how to win").

### 2.3 The share loop can no longer be silently dead

- `Store.get_or_create_secret()` mints and **persists** a signing key in the
  store when none is configured, and the app lifespan provisions it when
  `DRAFTMASTER_PROVISION_SECRET_KEY=true` (set in `render.yaml`). An operator who
  never opens the Render dashboard still gets working share links.
- The key is persisted (not per-process) so links minted before a restart keep
  verifying. Covered by `test_provisioned_key_is_stable_across_app_instances`.
- An explicitly configured `DRAFTMASTER_SECRET_KEY` always wins.

## 3. Verification

All of the following ran against real servers locally (FastAPI on `:12001`,
Next production build on `:12000`), not mocks:

- `python -m pytest services/engine/tests -q` → **127 passed, 1 skipped**
  (includes 4 new share tests: provisioning, cross-restart stability, My Hero
  round-trip, and rejecting a hero that is also an enemy).
- `python -m pytest services/growth/tests -q` → **31 passed**.
- `npx tsc --noEmit` → clean. `npm run build` → success (273 pages).
- `node scripts/check-i18n-placeholders.mjs` → ok.
- `POST /api/share` now returns a real 132-char signed token; the share page
  returns HTTP 200 with the branded CTA; `/og/share/{token}` returns a valid
  1080×1350 PNG (~573 KB) for both modes.

## 4. Remaining risk

The production **API is still on a stale Render build**. The web tier (Vercel)
tracks `main` and updates automatically, but the API did not redeploy even
though `autoDeploy: true` is set. Until the API redeploys, the new endpoints and
the share fixes are not live. No deploy hook or Render credential exists in the
repository, CI, or local dotfiles, so this needs either a manual redeploy from
the Render dashboard or a deploy hook. Setting `DRAFTMASTER_PROVISION_SECRET_KEY`
(or the blueprint re-apply) then makes sharing work without further steps.
