# DraftMaster AI — Database Schema

The MVP persists two tables via SQLAlchemy and creates them automatically at boot.
The same DDL runs on SQLite locally and PostgreSQL in production; the schema is
deliberately portable.

## 1. Operational tables (implemented)

### `profiles`

Stores the personal AI coach profile. One row per user.

```sql
CREATE TABLE IF NOT EXISTS profiles (
    user_id        TEXT PRIMARY KEY,
    role           TEXT,          -- carry | mid | offlane | support | hard_support
    rank_tier      INTEGER,       -- 11..80 (Valve medal tiers)
    favorite_heroes TEXT,         -- JSON array of hero ids
    comfort        TEXT,          -- JSON object { hero_id: 0..100 }
    playstyle      TEXT,          -- free-form tag
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

| Column | Notes |
| --- | --- |
| `user_id` | Client-generated opaque id (`u_xxxxxxxx`); becomes a real FK once auth lands |
| `rank_tier` | Feeds the win-probability rank compression and role weighting |
| `comfort` | The comfort-pick engine input; 20% of the final pick score |
| `favorite_heroes` | Drives tie-breaks and personal-coach nudges |

### `usage`

Daily analysis counter for free-plan quota enforcement.

```sql
CREATE TABLE IF NOT EXISTS usage (
    user_id TEXT,
    day     TEXT,                 -- YYYY-MM-DD (UTC)
    count   INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, day)
);
```

The composite primary key gives an idempotent upsert on every request. Quota checks
read the incremented value in the same transaction, so concurrent requests cannot
exceed the limit.

## 2. Production schema (planned)

The following tables are the production target. They are not required for the MVP to
run, and are listed here so the migration path is explicit rather than discovered.

### `users` (auth)

```sql
CREATE TABLE users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email          CITEXT UNIQUE,
    steam_id       TEXT UNIQUE,          -- Steam OpenID
    display_name   TEXT,
    plan           TEXT NOT NULL DEFAULT 'free',   -- free | premium
    plan_expires_at TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX users_steam_id_idx ON users (steam_id);
```

### `analyses` (history + analytics)

```sql
CREATE TABLE analyses (
    id             BIGSERIAL PRIMARY KEY,
    user_id        UUID REFERENCES users(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL,          -- analyse | panic | winprob | screenshot
    enemy_hero_ids INTEGER[] NOT NULL,
    player_hero_id INTEGER,
    role           TEXT,
    rank_tier      INTEGER,
    win_probability NUMERIC(5,2),
    final_score    NUMERIC(5,2),
    best_hero_id   INTEGER,
    payload        JSONB NOT NULL,         -- the full generated report
    generated_in_ms INTEGER,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX analyses_user_created_idx ON analyses (user_id, created_at DESC);
CREATE INDEX analyses_meta_idx ON analyses USING GIN (enemy_hero_ids);
CREATE INDEX analyses_best_hero_idx ON analyses (best_hero_id, created_at DESC);
```

The `enemy_hero_ids` GIN index and `best_hero_id` index are what make the meta
feedback loop possible: aggregating real user drafts reveals which heroes are
recommended and, joined with outcomes, whether the recommendations work.

### `match_coach_reports`

```sql
CREATE TABLE match_coach_reports (
    match_id    BIGINT NOT NULL,
    account_id  BIGINT,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (match_id, account_id)
);
```

### `subscriptions` / `payments`

```sql
CREATE TABLE subscriptions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    provider   TEXT NOT NULL,          -- stripe | paddle
    external_id TEXT NOT NULL,
    status     TEXT NOT NULL,          -- active | past_due | cancelled
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX subscriptions_external_idx ON subscriptions (provider, external_id);
```

### `hero_stats` (refreshed by the pipeline)

```sql
CREATE TABLE hero_stats (
    patch_id      INTEGER NOT NULL,
    hero_id       INTEGER NOT NULL,
    pub_winrate   NUMERIC(5,4),
    pub_pick      BIGINT,
    cm_winrate    NUMERIC(5,4),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (patch_id, hero_id)
);

CREATE TABLE counter_matrix (
    patch_id    INTEGER NOT NULL,
    hero_id     INTEGER NOT NULL,
    vs_hero_id  INTEGER NOT NULL,
    logit       NUMERIC(8,5) NOT NULL,
    samples     INTEGER,
    PRIMARY KEY (patch_id, hero_id, vs_hero_id)
);
```

## 3. Indexing strategy

| Access pattern | Index |
| --- | --- |
| "My recent analyses" | `analyses (user_id, created_at DESC)` |
| "Which heroes are recommended most?" | `analyses (best_hero_id, created_at DESC)` |
| "What drafts contain hero X?" | GIN on `analyses (enemy_hero_ids)` |
| Quota check | `usage` composite PK |
| Match coach cache hit | `match_coach_reports` composite PK |
| Counter lookup on the hot path | `counter_matrix` composite PK (also served from memory) |

## 4. Retention

- `analyses` — 24 months, then aggregated into `hero_stats` rollups.
- `match_coach_reports` — 12 months; the upstream data is re-fetchable.
- `usage` — 13 months (billing reconciliation window).
- Free-tier rows are pruned first.

## 5. Migration policy

- Alembic from the first production migration onwards.
- The MVP's `CREATE TABLE IF NOT EXISTS` bootstrap is idempotent, so enabling
  Alembic is additive and does not require a data backfill.
- All timestamps are stored UTC; `TIMESTAMPTZ` on Postgres, ISO text on SQLite.
- Every JSON column is documented and versioned (`payload.schema_version`) so the
  report format can evolve without breaking stored history.
