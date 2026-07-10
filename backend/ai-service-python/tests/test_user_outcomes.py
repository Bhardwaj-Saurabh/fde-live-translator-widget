"""Layer 2 — user outcomes.

What the widget user experiences: their page text comes back translated,
prices/SKUs intact, and repeat visits are near-instant. Mocked LLM by default;
the TestLiveLLM class calls the real provider and is the only true check of
es-MX quality (enable with RUN_LIVE_LLM_TESTS=1 python -m pytest -m live).
"""
import os

import pytest

from conftest import translate


async def test_translated_text_returned_verbatim_from_llm(client, fake_llm):
    r = await translate(client, "Good morning, welcome!")
    assert r.json()["translated"] == "[es-MX] Good morning, welcome!"


async def test_target_defaults_to_es_mx(client, fake_llm):
    await translate(client, "Home", target=None)  # omit target entirely
    assert fake_llm.calls == [("Home", "es-MX")]


async def test_prices_skus_numbers_pass_through_unaltered(client):
    text = "Now $1,299.00 — model WH-1000XM5, save 25%"
    translated = (await translate(client, text)).json()["translated"]
    for token in ("$1,299.00", "WH-1000XM5", "25%"):
        assert token in translated


async def test_cache_hit_dramatically_faster_than_miss(client, fake_llm):
    fake_llm.delay = 0.2  # simulate a real LLM round trip
    miss = (await translate(client, "Add to cart")).json()
    hit = (await translate(client, "Add to cart")).json()
    assert hit["cached"] is True
    assert hit["latencyMs"] < 20
    assert hit["latencyMs"] < miss["latencyMs"] / 5


@pytest.mark.live
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_LLM_TESTS"),
    reason="live LLM tests cost money; set RUN_LIVE_LLM_TESTS=1 to run",
)
class TestLiveLLM:
    """Calls the real lib.llm.translate_text — the executable version of the
    manual llm_prompt_quality rubric row. Needs a provider key in .env."""

    async def test_live_output_is_spanish_not_english(self):
        from lib.llm import translate_text

        out = await translate_text("Good morning, welcome to our store!")
        assert out.strip() and out.strip().lower() != "good morning, welcome to our store!"
        spanish_markers = ("¡", "á", "é", "í", "ó", "ú", "ñ", "bienvenid", "buenos")
        assert any(m in out.lower() for m in spanish_markers), f"not Spanish? {out!r}"

    async def test_live_preserves_price_and_sku(self):
        from lib.llm import translate_text

        out = await translate_text("Now $1,299.00 — model WH-1000XM5, save 25%")
        for token in ("$1,299.00", "WH-1000XM5", "25%"):
            assert token in out, f"{token} lost in {out!r}"

    async def test_live_translation_only_no_preamble_or_quotes(self):
        from lib.llm import translate_text

        out = (await translate_text("Add to cart")).strip()
        assert not out.startswith(('"', "'", "«")), f"wrapped in quotes: {out!r}"
        for preamble in ("here", "sure", "the translation", "translated", "claro"):
            assert not out.lower().startswith(preamble), f"preamble detected: {out!r}"
        assert "\n" not in out, f"multi-line answer for a 3-word input: {out!r}"
