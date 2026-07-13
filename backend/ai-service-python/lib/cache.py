"""
lib/cache.py — two-tier cache: memory + SQLite  (TODO: you implement)
=====================================================================
Why two tiers?
  - MEMORY (dict): instant, but lost on restart.
  - SQLite (disk): survives restarts, and is where you can inspect what your
    service has learned. Check memory first, then disk, then LLM.

The cache key must be deterministic for the same (text, target). Hashing the
input with sha256 gives you a compact, collision-safe key.

Optional TTL (`ttl_sec`): entries older than the TTL are treated as misses and
lazily deleted. Default None = never expire — translations don't go stale by
themselves; staleness comes from prompt/model changes, handled by clear().
"""
import hashlib
import time

import aiosqlite


def _key(text: str, target: str) -> str:
    return hashlib.sha256(f"{target}::{text}".encode("utf-8")).hexdigest()


class TwoTierCache:
    def __init__(self, db_path: str, ttl_sec: float | None = None):
        self.db_path = db_path
        self.ttl_sec = ttl_sec
        self._mem: dict[str, tuple[str, float]] = {}  # key -> (value, stored_monotonic)
        self._stats = {"requests": 0, "memory_hits": 0, "db_hits": 0, "misses": 0, "expired": 0}

    async def init(self) -> None:
        """Create the translations table if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS translations(
                    key TEXT PRIMARY KEY,
                    source TEXT,
                    target TEXT,
                    translated TEXT,
                    model TEXT,
                    access_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_translations_key ON translations(key)"
            )
            await db.commit()

    async def get(self, text: str, target: str) -> str | None:
        """Return a cached translation or None. Check memory, then SQLite."""
        self._stats["requests"] += 1
        k = _key(text, target)

        # 1) memory tier
        if k in self._mem:
            value, stored_at = self._mem[k]
            if self.ttl_sec is not None and time.monotonic() - stored_at > self.ttl_sec:
                del self._mem[k]  # expired here; the SQLite row is expired too — fall through
            else:
                self._stats["memory_hits"] += 1
                return value

        # 2) SQLite tier — age computed in SQL so no timestamp parsing here
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT translated, (julianday('now') - julianday(created_at)) * 86400.0
                   FROM translations WHERE key = ?""",
                (k,),
            ) as cur:
                row = await cur.fetchone()
            if row is None:
                self._stats["misses"] += 1
                return None
            if self.ttl_sec is not None and row[1] > self.ttl_sec:
                await db.execute("DELETE FROM translations WHERE key = ?", (k,))
                await db.commit()
                self._stats["expired"] += 1
                self._stats["misses"] += 1
                return None
            await db.execute(
                "UPDATE translations SET access_count = access_count + 1 WHERE key = ?", (k,)
            )
            await db.commit()

        self._mem[k] = (row[0], time.monotonic())  # warm the memory tier for next time
        self._stats["db_hits"] += 1
        return row[0]

    async def set(self, text: str, target: str, translated: str, model: str) -> None:
        """Store a translation in both tiers. A re-set refreshes the entry's age."""
        k = _key(text, target)
        self._mem[k] = (translated, time.monotonic())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO translations(key, source, target, translated, model)
                   VALUES(?, ?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                     translated = excluded.translated, model = excluded.model,
                     created_at = CURRENT_TIMESTAMP""",
                (k, text, target, translated, model),
            )
            await db.commit()

    async def clear(self) -> dict:
        """Empty both tiers (e.g. after a prompt or model change). Returns counts."""
        mem_count = len(self._mem)
        self._mem.clear()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM translations") as cur:
                db_count = (await cur.fetchone())[0]
            await db.execute("DELETE FROM translations")
            await db.commit()
        return {"memory": mem_count, "db": db_count}

    async def size(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM translations") as cur:
                row = await cur.fetchone()
                return row[0] if row else 0

    async def stats(self) -> dict:
        total = self._stats["memory_hits"] + self._stats["db_hits"] + self._stats["misses"]
        hits = self._stats["memory_hits"] + self._stats["db_hits"]
        hit_rate = round(100 * hits / total, 1) if total else 0.0
        return {**self._stats, "hit_rate_pct": hit_rate, "memory_entries": len(self._mem)}
