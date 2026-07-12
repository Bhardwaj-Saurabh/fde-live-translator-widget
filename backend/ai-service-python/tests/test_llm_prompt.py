"""Fast prompt-assembly tests for lib/llm.py — no network, no API key.

_build_messages() is a pure function; these tests pin the prompt contract
that docs/hindi-style-guide.md prescribes without spending a single token.
"""
import sys

from lib.llm import _BASE_SYSTEM, _FEW_SHOT, _STYLE_BLOCKS, _build_messages


def test_hindi_system_prompt_contains_style_block():
    system, _ = _build_messages("Add to cart", "hi-IN")
    assert system.startswith(_BASE_SYSTEM.format(target="hi-IN"))
    assert _STYLE_BLOCKS["hi-IN"] in system
    # spot-check the load-bearing rules survived into the prompt
    for marker in ("आप", "करें", "danda", "Devanagari", "कार्ट में जोड़ें"):
        assert marker in system


def test_messages_end_with_raw_user_text():
    text = "Free returns within 90 days"
    _, messages = _build_messages(text, "hi-IN")
    assert messages[-1] == {"role": "user", "content": text}


def test_few_shot_alternates_user_assistant_pairs():
    _, messages = _build_messages("Hello", "hi-IN")
    few_shot = messages[:-1]
    assert few_shot == _FEW_SHOT["hi-IN"]
    assert len(few_shot) % 2 == 0 and few_shot
    for i, msg in enumerate(few_shot):
        assert msg["role"] == ("user" if i % 2 == 0 else "assistant")


def test_few_shot_examples_follow_guide_conventions():
    """The examples ARE the style contract — they must obey guide §5/§8."""
    for msg in _FEW_SHOT["hi-IN"]:
        if msg["role"] == "assistant":
            out = msg["content"]
            assert not any("०" <= ch <= "९" for ch in out), f"Devanagari digit in {out!r}"
            assert any("ऀ" <= ch <= "ॿ" for ch in out), f"no Devanagari in {out!r}"
            assert not out.endswith("."), f"western period ends example {out!r}"


def test_unknown_target_gets_generic_prompt_no_few_shot():
    system, messages = _build_messages("Hello", "ta-IN")
    assert system == _BASE_SYSTEM.format(target="ta-IN")
    assert "आप" not in system
    assert messages == [{"role": "user", "content": "Hello"}]


def test_provider_sdk_not_imported_at_module_import_time():
    """The mocked suite and CI must not need the anthropic SDK or a key.
    lib.llm is already imported by conftest — the SDK loads lazily inside
    _get_client(), so it must be absent unless a live call happened."""
    assert "anthropic" not in sys.modules
