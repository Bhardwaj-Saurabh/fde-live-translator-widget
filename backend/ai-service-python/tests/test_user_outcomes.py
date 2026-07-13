"""Layer 2 — user outcomes.

What the widget user experiences: their page text comes back translated,
prices/SKUs intact, and repeat visits are near-instant. Mocked LLM by default;
the TestLiveLLM class calls the real provider and is the only true check of
hi-IN quality (enable with RUN_LIVE_LLM_TESTS=1 python -m pytest -m live).
"""
import os

import pytest

from conftest import translate


async def test_translated_text_returned_verbatim_from_llm(client, fake_llm):
    r = await translate(client, "Good morning, welcome!")
    assert r.json()["translated"] == "[hi-IN] Good morning, welcome!"


async def test_target_defaults_to_hi_in(client, fake_llm):
    await translate(client, "Home", target=None)  # omit target entirely
    assert fake_llm.calls == [("Home", "hi-IN")]


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

    async def test_live_output_is_hindi_not_english(self):
        from lib.llm import translate_text

        out = await translate_text("Good morning, welcome to our store!")
        assert out.strip() and out.strip().lower() != "good morning, welcome to our store!"
        # natural Hindi is written in Devanagari (U+0900–U+097F), not romanized
        assert any("ऀ" <= ch <= "ॿ" for ch in out), f"no Devanagari — not Hindi? {out!r}"

    async def test_live_preserves_price_and_sku(self):
        from lib.llm import translate_text

        out = await translate_text("Now $1,299.00 — model WH-1000XM5, save 25%")
        for token in ("$1,299.00", "WH-1000XM5", "25%"):
            assert token in out, f"{token} lost in {out!r}"

    async def test_live_translation_only_no_preamble_or_quotes(self):
        from lib.llm import translate_text

        out = (await translate_text("Add to cart")).strip()
        assert not out.startswith(('"', "'", "«")), f"wrapped in quotes: {out!r}"
        for preamble in ("here", "sure", "the translation", "translated", "अनुवाद:", "यहाँ"):
            assert not out.lower().startswith(preamble), f"preamble detected: {out!r}"
        assert "\n" not in out, f"multi-line answer for a 3-word input: {out!r}"


def _devanagari_ratio(text: str) -> float:
    """Share of alphabetic chars that are Devanagari (ignores digits/symbols)."""
    alpha = [ch for ch in text if ch.isalpha()]
    if not alpha:
        return 0.0
    return sum(1 for ch in alpha if "ऀ" <= ch <= "ॿ") / len(alpha)


@pytest.mark.live
@pytest.mark.skipif(
    not os.getenv("RUN_LIVE_LLM_TESTS"),
    reason="live LLM tests cost money; set RUN_LIVE_LLM_TESTS=1 to run",
)
class TestLiveStyle:
    """Style adherence against docs/hindi-style-guide.md — each test names
    the guide section it enforces. Update the guide + prompt together."""

    async def test_prose_is_mostly_devanagari_and_ends_with_danda(self):
        # guide §5: danda for prose; §4: Devanagari body
        from lib.llm import translate_text

        out = (await translate_text("Our team will contact you within two days.")).strip()
        assert _devanagari_ratio(out) >= 0.5, f"too little Devanagari: {out!r}"
        assert out.endswith("।"), f"prose must end with danda: {out!r}"

    async def test_no_devanagari_digits_and_currency_preserved(self):
        # guide §5: Western digits only; $ never converted
        from lib.llm import translate_text

        out = await translate_text("Order 3 items for $49.99 and get 10% off.")
        assert not any("०" <= ch <= "९" for ch in out), f"Devanagari digits: {out!r}"
        for token in ("3", "$49.99", "10%"):
            assert token in out, f"{token} lost/reformatted in {out!r}"
        assert "₹" not in out, f"currency converted to rupees: {out!r}"

    async def test_brand_name_stays_latin(self):
        # guide §4: brands never transliterated
        from lib.llm import translate_text

        out = await translate_text("Shop the Home Depot summer sale today")
        assert "Home Depot" in out, f"brand transliterated/translated: {out!r}"
        assert "होम डिपो" not in out

    async def test_ui_label_uses_canonical_lexicon_no_terminal_punctuation(self):
        # guide §6: canonical e-commerce strings; §5: bare UI labels
        from lib.llm import translate_text

        out = (await translate_text("Add to cart")).strip()
        assert "कार्ट" in out, f"expected loanword कार्ट (guide §6): {out!r}"
        assert not out.endswith(("।", ".", "!")), f"UI label got punctuation: {out!r}"

    async def test_imperative_uses_karein_register(self):
        # guide §2: करें/-एं imperatives, never कीजिए/करो
        from lib.llm import translate_text

        out = await translate_text("Choose a delivery location to continue")
        assert "कीजिए" not in out and "करो" not in out, f"wrong register: {out!r}"

    async def test_nav_label_takes_website_sense(self):
        # guide §6: single-word nav labels get their site-navigation meaning
        from lib.llm import translate_text

        out = (await translate_text("Home")).strip()
        assert "होम" in out, f"nav label lost its website sense: {out!r}"
        assert not out.endswith(("।", ".")), f"UI label got punctuation: {out!r}"

    async def test_mixed_hindi_english_input_keeps_hindi_translates_english(self):
        # base prompt: already-target-language text is kept, only the rest translated
        from lib.llm import translate_text

        out = await translate_text("आपका ऑर्डर ready है — track it here")
        assert "आपका ऑर्डर" in out, f"existing Hindi was rewritten: {out!r}"
        assert "ट्रैक" in out, f"English tail not translated: {out!r}"
        assert "track it here" not in out.lower(), f"English left untranslated: {out!r}"
