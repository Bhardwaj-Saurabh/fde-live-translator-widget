"""
Provider routing: OpenRouter is the primary (cheaper) provider when
OPENROUTER_API_KEY is set; Anthropic direct is the fallback. If BOTH fail,
the exception propagates — the fail-loud rule survives the fallback chain
(silently returning the English input is an automatic fail).

These tests patch the two provider seams (_openrouter_call/_anthropic_call),
so they run without a network or keys.
"""
import pytest

import lib.llm as llm


def _providers(monkeypatch, openrouter, anthropic):
    monkeypatch.setattr(llm, "_openrouter_call", openrouter)
    monkeypatch.setattr(llm, "_anthropic_call", anthropic)


async def test_openrouter_used_when_key_set(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    calls = []

    async def fake_or(model, system, messages):
        calls.append(("openrouter", model))
        return "नमस्ते"

    async def fake_an(model, system, messages):
        calls.append(("anthropic", model))
        return "नमस्ते"

    _providers(monkeypatch, fake_or, fake_an)
    out = await llm.translate_text("Hello", "hi-IN")
    assert out == "नमस्ते"
    assert [c[0] for c in calls] == ["openrouter"]  # anthropic never touched


async def test_falls_back_to_anthropic_when_openrouter_fails(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    calls = []

    async def fake_or(model, system, messages):
        calls.append("openrouter")
        raise RuntimeError("openrouter down")

    async def fake_an(model, system, messages):
        calls.append("anthropic")
        return "नमस्ते"

    _providers(monkeypatch, fake_or, fake_an)
    out = await llm.translate_text("Hello", "hi-IN")
    assert out == "नमस्ते"
    assert calls == ["openrouter", "anthropic"]


async def test_both_providers_failing_raises_never_returns_english(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def fake_or(model, system, messages):
        raise RuntimeError("openrouter down")

    async def fake_an(model, system, messages):
        raise RuntimeError("anthropic down")

    _providers(monkeypatch, fake_or, fake_an)
    with pytest.raises(RuntimeError):
        await llm.translate_text("Hello", "hi-IN")


async def test_anthropic_direct_when_no_openrouter_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    calls = []

    async def fake_or(model, system, messages):
        calls.append("openrouter")
        return "नमस्ते"

    async def fake_an(model, system, messages):
        calls.append(("anthropic", model))
        return "नमस्ते"

    _providers(monkeypatch, fake_or, fake_an)
    out = await llm.translate_text("Hello", "hi-IN")
    assert out == "नमस्ते"
    assert calls == [("anthropic", llm.ANTHROPIC_MODEL)]


async def test_wrapping_quotes_stripped_regardless_of_provider(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    async def fake_or(model, system, messages):
        return "“नमस्ते”"

    async def fake_an(model, system, messages):
        raise AssertionError("should not reach anthropic")

    _providers(monkeypatch, fake_or, fake_an)
    assert await llm.translate_text("Hello", "hi-IN") == "नमस्ते"
