"""Layer 4 — edge cases and failure modes.

Degenerate input, unicode, validation, and the assignment's automatic-fail
rule: an LLM failure must surface as an error, never as the untranslated
English served with a 200.
"""
import asyncio

from conftest import translate


async def test_empty_text_returns_empty_without_llm_call(client, fake_llm):
    body = (await translate(client, "")).json()
    assert body["translated"] == ""
    assert body["cached"] is False
    assert fake_llm.calls == []


async def test_whitespace_only_text_treated_as_empty(client, fake_llm):
    body = (await translate(client, "   \n\t  ")).json()
    assert body["translated"] == ""
    assert fake_llm.calls == []


async def test_very_long_text_roundtrips(client):
    text = "Premium quality product with free shipping. " * 250  # ~11k chars
    body = (await translate(client, text)).json()
    assert body["translated"].endswith("shipping.")
    assert (await translate(client, text)).json()["cached"] is True


async def test_special_chars_emoji_html_entities_cache_correctly(client, fake_llm):
    text = "Café ☕ &amp; 50% off — «déjà vu»"
    first = (await translate(client, text)).json()
    second = (await translate(client, text)).json()
    assert text in first["translated"]  # fake LLM is verbatim-preserving
    assert second["cached"] is True, "sha256 cache key unstable for unicode input"
    assert len(fake_llm.calls) == 1


async def test_batch_empty_array_returns_empty_results(client):
    r = await client.post("/translate/batch", json={"texts": [], "target": "es-MX"})
    assert r.status_code == 200
    assert r.json()["results"] == []


async def test_batch_mixed_empty_and_real_content(client, fake_llm):
    r = await client.post(
        "/translate/batch", json={"texts": ["", "Add to cart", "  "], "target": "es-MX"}
    )
    results = r.json()["results"]
    assert [item["translated"] for item in results] == ["", "[es-MX] Add to cart", ""]
    assert fake_llm.calls == [("Add to cart", "es-MX")]


async def test_missing_text_field_is_4xx(client):
    r = await client.post("/translate", json={"target": "es-MX"})
    assert 400 <= r.status_code < 500


async def test_text_wrong_type_is_4xx(client):
    r = await client.post("/translate", json={"text": 123, "target": "es-MX"})
    assert 400 <= r.status_code < 500


# The automatic-fail rule (AGENTS.md): a provider failure must propagate —
# never a 200 carrying the untranslated English, and never a cache write.
async def test_llm_failure_propagates_never_returns_english(client_no_raise, fake_llm, test_cache):
    fake_llm.fail = RuntimeError("provider down")
    text = "Flash sale ends tonight"

    r = await client_no_raise.post("/translate", json={"text": text, "target": "es-MX"})
    assert r.status_code >= 500, "LLM failure was swallowed instead of surfacing"
    if r.headers.get("content-type", "").startswith("application/json"):
        assert r.json().get("translated") != text, "silent English fallback — automatic fail"
    assert await test_cache.get(text, "es-MX") is None, "failed translation was cached"

    # service must recover once the provider is healthy again
    fake_llm.fail = None
    ok = await client_no_raise.post("/translate", json={"text": text, "target": "es-MX"})
    assert ok.status_code == 200


# AGENTS.md: identical (text, target) MUST NOT call the LLM twice — including
# concurrently (a page of repeated strings arrives as a burst). This requires
# single-flight dedup (e.g. a per-key map of pending futures in translate_one),
# which is deliberately beyond the TODO skeleton: the test stays RED until you
# build it. It is not flaky and must not be weakened.
async def test_concurrent_identical_requests_call_llm_once(client, fake_llm):
    fake_llm.delay = 0.2
    responses = await asyncio.gather(
        *(translate(client, "Limited time offer") for _ in range(5))
    )
    bodies = [r.json() for r in responses]
    assert len({b["translated"] for b in bodies}) == 1
    assert len(fake_llm.calls) == 1, (
        f"{len(fake_llm.calls)} LLM calls for 5 concurrent identical requests — "
        "add single-flight dedup so concurrent duplicates await one in-flight call"
    )
