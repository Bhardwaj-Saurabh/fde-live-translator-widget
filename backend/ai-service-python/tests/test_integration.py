"""Layer 3 — application integration.

The two-tier cache working as a system: SQLite persistence across a simulated
process restart (AGENTS.md DoD step 3), memory-tier warming, accurate /stats,
and truthful per-item batch flags.
"""
import app as app_module
from lib.cache import TwoTierCache

from conftest import translate


async def _restart_cache(monkeypatch, db_path):
    """Simulate a process restart: a brand-new cache (empty memory tier) on
    the same SQLite file, swapped into the app."""
    fresh = TwoTierCache(str(db_path))
    await fresh.init()
    monkeypatch.setattr(app_module, "cache", fresh)
    return fresh


async def test_sqlite_persists_across_restart(client, fake_llm, monkeypatch, db_path):
    first = (await translate(client, "Free returns within 90 days")).json()
    assert first["cached"] is False

    await _restart_cache(monkeypatch, db_path)

    after_restart = (await translate(client, "Free returns within 90 days")).json()
    assert after_restart["cached"] is True, "SQLite tier did not survive the restart"
    assert after_restart["translated"] == first["translated"]
    assert len(fake_llm.calls) == 1, "restart caused a second LLM call for identical input"


async def test_memory_tier_warmed_after_db_hit(client, fake_llm, monkeypatch, db_path):
    await translate(client, "Shop all departments")
    fresh = await _restart_cache(monkeypatch, db_path)

    await translate(client, "Shop all departments")  # served from SQLite
    stats = (await client.get("/stats")).json()
    assert stats["db_hits"] == 1

    await translate(client, "Shop all departments")  # now from warmed memory
    stats = (await client.get("/stats")).json()
    assert stats["memory_hits"] == 1
    assert fresh._mem, "db hit did not warm the memory tier"


async def test_stats_counters_accumulate(client):
    await translate(client, "Weekly deals")   # miss
    await translate(client, "Weekly deals")   # memory hit
    await translate(client, "Gift cards")     # miss

    stats = (await client.get("/stats")).json()
    assert stats["requests"] == 3
    assert stats["misses"] == 2
    assert stats["memory_hits"] == 1
    assert stats["hit_rate_pct"] == round(100 * 1 / 3, 1)


async def test_batch_reports_per_item_cached_flags(client):
    await translate(client, "Home")  # pre-warm one string

    r = await client.post(
        "/translate/batch", json={"texts": ["Home", "Best sellers"], "target": "es-MX"}
    )
    flags = [item["cached"] for item in r.json()["results"]]
    assert flags == [True, False], "per-item cached flags wrong or out of order"
