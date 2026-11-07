"""Infrastructure adapters: cache and persistence.

Both degrade gracefully so the service runs with zero external dependencies
locally (in-memory cache + SQLite) and scales to Redis + PostgreSQL in
production by setting DRAFTMASTER_REDIS_URL / DRAFTMASTER_DATABASE_URL.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

from .config import Settings

log = logging.getLogger("draftmaster.infra")


class Cache:
    """Minimal cache interface with an in-memory default and Redis backend."""

    def __init__(self, settings: Settings):
        self._mem: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()
        self._redis = None
        if settings.redis_url:
            try:  # pragma: no cover - requires redis server
                import redis

                self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
                self._redis.ping()
            except Exception:
                self._redis = None

    @property
    def backend(self) -> str:
        return "redis" if self._redis else "memory"

    def get(self, key: str) -> Any | None:
        if self._redis:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else None
        with self._lock:
            item = self._mem.get(key)
            if not item:
                return None
            expires, raw = item
            if expires < time.time():
                self._mem.pop(key, None)
                return None
            return json.loads(raw)

    def set(self, key: str, value: Any, ttl: int) -> None:
        raw = json.dumps(value, default=str)
        if self._redis:
            self._redis.setex(key, ttl, raw)
            return
        with self._lock:
            self._mem[key] = (time.time() + ttl, raw)

    def incr(self, key: str, ttl: int) -> int:
        if self._redis:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)
            count, _ = pipe.execute()
            return int(count)
        with self._lock:
            item = self._mem.get(key)
            now = time.time()
            if not item or item[0] < now:
                self._mem[key] = (now + ttl, "1")
                return 1
            expires, raw = item
            count = int(json.loads(raw)) + 1
            self._mem[key] = (expires, json.dumps(count))
            return count


class Store:
    """User profile + usage persistence (PostgreSQL or SQLite)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = None
        self._profiles: dict[str, dict] = {}
        self._usage: dict[tuple[str, str], int] = {}
        self._lock = threading.Lock()
        self.backend = "memory"
        url = settings.database_url or "sqlite:///" + str(
            (__import__("pathlib").Path(settings.artifact_path).parent.parent / "draftmaster.db")
        )
        try:  # pragma: no cover - depends on driver availability
            from sqlalchemy import create_engine, text

            self.engine = create_engine(url, future=True, pool_pre_ping=True)
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS profiles (
                            user_id TEXT PRIMARY KEY,
                            role TEXT,
                            rank_tier INTEGER,
                            favorite_heroes TEXT,
                            comfort TEXT,
                            playstyle TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                        """
                    )
                )
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS usage (
                            user_id TEXT,
                            day TEXT,
                            count INTEGER DEFAULT 0,
                            PRIMARY KEY (user_id, day)
                        )
                        """
                    )
                )
            self.backend = "sqlalchemy"
        except Exception as exc:
            # Never fail to start, but never hide a broken production database
            # either: a silent memory fallback would lose profiles and quota.
            log.warning("store falling back to memory (url=%s): %s", url, exc)
            self.engine = None

    # -- profiles --------------------------------------------------------
    def upsert_profile(self, payload: dict) -> dict:
        uid = payload["user_id"]
        row = {
            "user_id": uid,
            "role": payload.get("role"),
            "rank_tier": payload.get("rank_tier"),
            "favorite_heroes": payload.get("favorite_heroes", []),
            "comfort": payload.get("comfort", {}),
            "playstyle": payload.get("playstyle"),
        }
        if self.engine:  # pragma: no cover - requires DB
            from sqlalchemy import text

            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO profiles (user_id, role, rank_tier, favorite_heroes, comfort, playstyle, updated_at)
                        VALUES (:user_id, :role, :rank_tier, :favorite_heroes, :comfort, :playstyle, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            role=excluded.role, rank_tier=excluded.rank_tier,
                            favorite_heroes=excluded.favorite_heroes, comfort=excluded.comfort,
                            playstyle=excluded.playstyle, updated_at=CURRENT_TIMESTAMP
                        """
                    ),
                    {
                        **row,
                        "favorite_heroes": json.dumps(row["favorite_heroes"]),
                        "comfort": json.dumps(row["comfort"]),
                    },
                )
        with self._lock:
            self._profiles[uid] = row
        return row

    def get_profile(self, user_id: str) -> dict | None:
        if self.engine:  # pragma: no cover - requires DB
            from sqlalchemy import text

            with self.engine.connect() as conn:
                res = conn.execute(
                    text("SELECT * FROM profiles WHERE user_id = :u"), {"u": user_id}
                ).mappings().first()
                if res:
                    return {
                        "user_id": res["user_id"],
                        "role": res["role"],
                        "rank_tier": res["rank_tier"],
                        "favorite_heroes": json.loads(res["favorite_heroes"] or "[]"),
                        "comfort": json.loads(res["comfort"] or "{}"),
                        "playstyle": res["playstyle"],
                    }
        return self._profiles.get(user_id)

    # -- usage -----------------------------------------------------------
    def increment_usage(self, user_id: str, day: str) -> int:
        if self.engine:  # pragma: no cover - requires DB
            from sqlalchemy import text

            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        INSERT INTO usage (user_id, day, count) VALUES (:u, :d, 1)
                        ON CONFLICT (user_id, day) DO UPDATE SET count = usage.count + 1
                        """
                    ),
                    {"u": user_id, "d": day},
                )
                res = conn.execute(
                    text("SELECT count FROM usage WHERE user_id = :u AND day = :d"),
                    {"u": user_id, "d": day},
                ).scalar()
                return int(res or 1)
        with self._lock:
            key = (user_id, day)
            self._usage[key] = self._usage.get(key, 0) + 1
            return self._usage[key]

    def get_usage(self, user_id: str, day: str) -> int:
        if self.engine:  # pragma: no cover - requires DB
            from sqlalchemy import text

            with self.engine.connect() as conn:
                res = conn.execute(
                    text("SELECT count FROM usage WHERE user_id = :u AND day = :d"),
                    {"u": user_id, "d": day},
                ).scalar()
                return int(res or 0)
        return self._usage.get((user_id, day), 0)
