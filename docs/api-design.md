# DraftMaster AI — API Design

Base URL: `/api`. The FastAPI app also serves interactive OpenAPI docs at `/docs`
and the raw schema at `/openapi.json`.

## 1. Conventions

- **Content type:** `application/json` (except the screenshot endpoint, which is
  `multipart/form-data`).
- **Headers:**
  - `x-user-id` — opaque client id used for profile and quota. Optional; defaults to
    `anonymous`.
  - `authorization: Bearer <token>` — `Bearer premium-token` selects the premium
    plan in this MVP. Production replaces this with real auth.
- **Errors:** `{"detail": "..."}` with a meaningful HTTP status.
  `402` quota exceeded · `404` not found · `413` payload too large ·
  `422` validation/unknown hero · `502` upstream (OpenDota) failure.
- **Timing:** every report response carries `generated_in_ms`.

## 2. Service metadata

### `GET /`
```json
{
  "service": "DraftMaster AI",
  "version": "1.0.0",
  "heroes": 127,
  "patch": "7.41",
  "flagship": ["POST /api/panic", "POST /api/analyse", "POST /api/win-probability"]
}
```

### `GET /health`
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "hero_count": 127,
  "patch": "7.41",
  "dataset_generated_at": "2026-11-07T15:08:21Z"
}
```

## 3. Reference data

### `GET /api/heroes` → `HeroOut[]`
`id`, `name`, `localized_name`, `roles[]`, `primary_attr`, `attack_type`, `icon`,
`img`, `tags[]`, `pub_winrate`.

### `GET /api/heroes/{id}` → hero object (404 if unknown)

### `GET /api/heroes/{id}/matchups`
```json
{
  "hero_id": 26,
  "hero": "Lion",
  "best_against":  [{ "hero_id": 8, "hero": "Juggernaut", "score": 61.2 }],
  "worst_against": [{ "hero_id": 9, "hero": "Mirana",     "score": 44.8 }]
}
```
Scores are the shrunk advantage mapped onto a 0–100 readability scale.

### `GET /api/items` → item index (`key`, `dname`, `cost`, `img`, …)

### `GET /api/meta`
```json
{
  "patch": "7.41",
  "generated_at": "2026-11-07T15:08:21Z",
  "source": "OpenDota public match data",
  "trending":      [{ "hero_id": 14, "hero": "Pudge", "picks": 1067108 }],
  "patch_winners": [{ "hero_id": 42, "hero": "Wraith King", "cm_winrate": 0.5511 }],
  "patch_losers":  [{ "hero_id": 53, "hero": "Nature's Prophet", "cm_winrate": 0.432 }]
}
```

## 4. Analysis

### `POST /api/analyse`
Full 11-section report.

Request:
```json
{
  "enemy_hero_ids": [26, 2, 27],
  "hero_id": 8,
  "role": "carry",
  "rank_tier": 70,
  "allies": [],
  "comfort": { "8": 90 }
}
```
`enemy_hero_ids` is required (1–5). `hero_id` is optional: when omitted the engine
selects the best pick.

Response (abridged):
```json
{
  "report": {
    "generated_in_ms": 12,
    "patch": "7.41",
    "enemy_draft": [ { "id": 26, "localized_name": "Lion", "roles": [], "tags": [], "capabilities": {} } ],
    "win_probability": {
      "player_win_probability": 71.7,
      "enemy_win_probability": 28.3,
      "confidence": "high",
      "rank_label": "Legend",
      "verdict": "Favoured draft — press your advantage with the plan below.",
      "factors": [ { "name": "Hero matchups", "detail": "…", "contribution_pp": 28.6 } ]
    },
    "best_picks": [ { "hero_id": 80, "localized_name": "Lone Druid",
                      "scores": { "counter": 78.6, "meta": 45.7, "comfort": 50.0,
                                  "synergy": 50.0, "difficulty": 100.0, "lane": 85.0,
                                  "role": 70.0, "final": 62.6 },
                      "reasons": ["…"], "strong_against": ["Shadow Shaman"] } ],
    "why_this_hero": ["…"],
    "threat_analysis": { "scores": {}, "labels": {}, "danger": {}, "problems": {} },
    "item_build": { "starting": [], "lane": [], "early": [], "mid": [], "late": [],
                    "luxury": [], "situational": [], "emergency": [],
                    "avoid": [], "key_counters": [] },
    "skill_build": { "levels": [], "notes": [], "primary": "", "secondary": "", "ultimate": "" },
    "talents": [ { "hero_level": 10, "options": [], "recommended": "", "reason": "" } ],
    "match_plan": [ { "window": "0-10", "phase": "Laning", "objectives": [],
                      "farm_focus": "", "fight_focus": "", "map_movement": "",
                      "tower_priority": "", "roshan_priority": "", "danger_zones": [] } ],
    "win_conditions": { "primary": "", "secondary": "", "emergency": "" },
    "target_priority": [ { "hero_id": 2, "name": "Axe", "priority_score": 44.1, "rank": 1, "reason": "" } ],
    "power_spikes": { "player": [], "enemies": [] },
    "one_sentence_win_plan": "…",
    "draft_summary": { "headline_threats": [], "top_target": "Axe",
                       "win_probability": 71.7, "hero": "Lone Druid", "verdict": "…" }
  },
  "usage": { "plan": "free", "used_today": 1, "daily_limit": 3, "remaining": 2 },
  "cached": false
}
```

### `POST /api/panic`
Panic Mode. Same inputs as `/api/analyse` minus `hero_id`. Returns a flattened,
one-screen payload: `best_hero`, `backups`, `win_probability`, `full_build`,
`danger_heroes`, `power_spikes`, `kill_priority`, `win_conditions`,
`items_to_avoid`, `one_sentence_win_plan`, `why_this_hero`, `threat_analysis`,
`generated_in_ms`, `usage`.

### `POST /api/win-probability`
```json
{ "enemy_hero_ids": [26, 2, 27], "hero_id": 8, "role": "carry", "rank_tier": 70 }
```
→ a `WinProbability` object (same shape as `report.win_probability`).

## 5. Screenshot

### `POST /api/screenshot/analyse`
`multipart/form-data` with a single `file` field (PNG/JPEG/WebP, ≤ 8 MB).

Response:
```json
{
  "detection": {
    "detected": [ { "hero_id": 26, "localized_name": "Lion", "confidence": 0.9884,
                    "margin": 0.31, "x": 12, "y": 12, "size": 80 } ],
    "hero_ids": [26, 2, 27, 35, 59],
    "count": 5,
    "image_size": { "width": 472, "height": 104 },
    "confidence_floor": 0.82,
    "confidence_margin": 0.08
  },
  "report": { "…": "full report, or null when nothing was detected" },
  "usage": { "…": "…" },
  "note": "Detected heroes were auto-fed into the report engine."
}
```
At most the first five detections are fed to the engine.

## 6. Match coach

### `POST /api/match/coach`
```json
{ "match_id": 9080108550, "account_id": null }
```
→ `{ "coach_report": { match_id, duration_min, radiant_win, player, verdict,
grades: { farm, xp, last_hits, fighting, survival }, strengths[], mistakes[],
item_notes[], timing_notes[], practice_plan[] }, "cached": false }`

### `GET /api/match/{match_id}` → condensed match summary with per-player lines.

## 7. Profiles

### `GET /api/profile/{user_id}` → profile or `404`
### `PUT /api/profile`
```json
{ "user_id": "u_abc", "role": "carry", "rank_tier": 70,
  "favorite_heroes": [8, 41], "comfort": { "8": 90 }, "playstyle": "aggressive" }
```

## 8. Rate limiting and quota

| Plan | Analyses/day | Match coach | AI coach |
| --- | --- | --- | --- |
| Free | 3 | preview | — |
| Premium | unlimited | unlimited | yes |

Quota is incremented before work is done and enforced atomically in `Store`, so the
limit cannot be exceeded by concurrent requests. Exceeding it returns `402` with an
explicit upgrade message rather than a generic error.

## 9. Versioning

The API is unversioned at `/api` for the MVP. When a breaking change is required, the
new surface moves to `/api/v2` and the old routes remain for one release cycle.
Report payloads carry a `schema_version` field once persisted, so stored history
remains readable across engine changes.
