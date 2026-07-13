"""
Cache TTL + authenticated POST /clear-cache.

TTL is a constructor param (default None = entries never age out — staleness
comes from prompt/model changes, which clear-cache handles). The endpoint is
operationally absent until ADMIN_TOKEN is configured (403), and rejects bad
tokens with 401. The cache key stays sha256(target::text) — contract.
"""
import asyncio

import pytest

import app as app_module
from lib.cache import TwoTierCache


# --- TTL -------------------------------------------------------------------

async def test_entry_expires_after_ttl_in_both_tiers(db_path):
    cache = TwoTierCache(str(db_path), ttl_sec=0.05)
    await cache.init()
    await cache.set("Hello", "hi-IN", "नमस्ते", model="m")
    assert await cache.get("Hello", "hi-IN") == "नमस्ते"  # fresh: memory hit

    await asyncio.sleep(0.12)
    assert await cache.get("Hello", "hi-IN") is None  # memory tier expired

    # SQLite tier expired too — a fresh process on the same db must also miss
    cache2 = TwoTierCache(str(db_path), ttl_sec=0.05)
    await cache2.init()
    assert await cache2.get("Hello", "hi-IN") is None


async def test_no_ttl_means_entries_never_expire(db_path):
    cache = TwoTierCache(str(db_path))  # default: no TTL
    await cache.init()
    await cache.set("Hello", "hi-IN", "नमस्ते", model="m")
    await asyncio.sleep(0.12)
    assert await cache.get("Hello", "hi-IN") == "नमस्ते"


async def test_expired_entries_count_in_stats(db_path):
    cache = TwoTierCache(str(db_path), ttl_sec=0.05)
    await cache.init()
    await cache.set("Hello", "hi-IN", "नमस्ते", model="m")
    await asyncio.sleep(0.12)
    await cache.get("Hello", "hi-IN")
    stats = await cache.stats()
    assert stats["expired"] == 1
    assert stats["misses"] == 1  # an expired entry is a miss to the caller


async def test_reset_refreshes_created_at(db_path):
    import aiosqlite

    cache = TwoTierCache(str(db_path), ttl_sec=5)
    await cache.init()
    await cache.set("Hello", "hi-IN", "पुराना", model="m")
    # simulate an old row, then re-set: the upsert must refresh created_at
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("UPDATE translations SET created_at = datetime('now', '-1 hour')")
        await db.commit()
    await cache.set("Hello", "hi-IN", "नया", model="m")

    fresh = TwoTierCache(str(db_path), ttl_sec=5)  # bypass the memory tier
    await fresh.init()
    assert await fresh.get("Hello", "hi-IN") == "नया"


# --- clear() ----------------------------------------------------------------

async def test_clear_empties_both_tiers_and_persists(db_path):
    cache = TwoTierCache(str(db_path))
    await cache.init()
    await cache.set("One", "hi-IN", "एक", model="m")
    await cache.set("Two", "hi-IN", "दो", model="m")

    cleared = await cache.clear()
    assert cleared == {"memory": 2, "db": 2}
    assert await cache.get("One", "hi-IN") is None
    assert await cache.size() == 0

    fresh = TwoTierCache(str(db_path))  # the delete reached the disk tier
    await fresh.init()
    assert await fresh.get("Two", "hi-IN") is None


# --- POST /clear-cache -------------------------------------------------------

async def test_clear_cache_403_when_no_admin_token_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    r = await client.post("/clear-cache")
    assert r.status_code == 403


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong-token"}])
async def test_clear_cache_401_on_missing_or_wrong_token(client, monkeypatch, headers):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    r = await client.post("/clear-cache", headers=headers)
    assert r.status_code == 401


async def test_clear_cache_with_token_clears_and_next_request_misses(client, fake_llm, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    first = await client.post("/translate", json={"text": "Hello", "target": "hi-IN"})
    assert first.json()["cached"] is False
    assert len(fake_llm.calls) == 1

    r = await client.post("/clear-cache", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200
    body = r.json()
    assert body["cleared"]["db"] == 1

    again = await client.post("/translate", json={"text": "Hello", "target": "hi-IN"})
    assert again.json()["cached"] is False  # cache really gone → LLM called again
    assert len(fake_llm.calls) == 2
