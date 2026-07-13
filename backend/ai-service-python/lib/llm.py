"""
lib/llm.py — the LLM translation call
=====================================
Translates English into natural, modern web Hindi (hi-IN by default).

The style rules and few-shot examples below are DISTILLED FROM
docs/hindi-style-guide.md (the research source of truth) — when you change
one, change both, then re-run the live style tests and clear translations.db
(the cache key has no prompt version, so stale-style entries persist).

PROVIDER ROUTING: when OPENROUTER_API_KEY is set, OpenRouter is the primary
provider (cheaper per-token routing, e.g. Haiku at 1/3 the Sonnet price);
Anthropic direct is the fallback. A fallback still translates — but if BOTH
providers fail, the exception propagates so the caller returns a 502.
Silently returning the untranslated input is an automatic fail (it ships
English while looking healthy).
"""
import os

from dotenv import load_dotenv

from lib.logger import get_logger

load_dotenv()  # app.py imports this module before its own load_dotenv() runs

log = get_logger("ai-service")

ANTHROPIC_MODEL = os.getenv("MODEL", "claude-sonnet-4-6")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5")

# What /health and responses report: the primary provider's model.
MODEL_DEFAULT = OPENROUTER_MODEL if os.getenv("OPENROUTER_API_KEY") else ANTHROPIC_MODEL

_BASE_SYSTEM = (
    "You are a professional translator. Translate the user's text into {target}. "
    "Return ONLY the translation — no preamble, no explanations, no wrapping quotes. "
    "Preserve exactly as-is: numbers, prices and currency symbols ($ stays $), "
    "percentages, model/SKU codes, brand names, units (1.5GB, 7200mAh), URLs, "
    "emails, HTML tags/entities, and emoji. "
    "A fragment (button label, heading, menu item) stays a fragment — never expand "
    "it into a sentence. If the input already contains {target} text, keep it and "
    "translate only the rest."
)

# Per-target style rules, distilled from docs/hindi-style-guide.md §2-§8.
# Adding a language = adding a dict entry here and in _FEW_SHOT; no code change.
# Token-compressed deliberately: this block rides on EVERY cache miss.
_STYLE_BLOCKS: dict[str, str] = {
    "hi-IN": (
        "\n\nHindi style — modern web Hindi like Amazon.in/Flipkart UIs and popular "
        "Hindi news/blog sites, not formal translation:\n"
        "- Devanagari script only; never romanized Hinglish.\n"
        "- Reader is आप; imperatives in the करें form (खरीदें, जोड़ें) — never कीजिए/करो.\n"
        "- Everyday English nouns stay as Devanagari loanwords (कार्ट, ऑर्डर, डिलीवरी, "
        "ऐप, सेल, अकाउंट); verbs and value-words go native (खरीदें, कीमत, छूट, भुगतान). "
        "No sanskritized coinages: ऐप not अनुप्रयोग, कार्ट not टोकरी.\n"
        "- Brand names (Home Depot, DeWalt, Google), model/SKU codes, and acronyms "
        "(OTP, AI) stay in Latin script — never transliterate them.\n"
        "- Digits 0-9 only, never Devanagari digits; large numbers as लाख/करोड़.\n"
        "- Prose sentences end with the danda ।; UI fragments and labels get no "
        "terminal punctuation.\n"
        "- Canonical UI strings where they fit: Add to cart → कार्ट में जोड़ें, "
        "Buy now → अभी खरीदें, Reviews → समीक्षाएं. Single-word nav labels take "
        "their website sense: Home → होम.\n"
        "- Natural Hindi word order; split long sentences rather than mirroring "
        "English. Add nothing the source doesn't say."
    ),
}

# Few-shot as real user/assistant turns — the transcript itself teaches
# bare-input → bare-translation. Derived from the guide's §9 canonical pairs;
# trimmed to the 3 load-bearing shapes (UI fragment with $ · brand/SKU/price ·
# prose with danda). Rules cover the rest. NOTE: no bare "Home" → होम example —
# it taught the model to transliterate "Home Depot" (caught by the live style
# tests); the nav-label sense lives in the rules instead.
_FEW_SHOT: dict[str, list[dict]] = {
    "hi-IN": [
        {"role": "user", "content": "Free shipping on orders over $45"},
        {"role": "assistant", "content": "$45 से ज़्यादा के ऑर्डर पर मुफ़्त शिपिंग"},
        {"role": "user", "content": "DeWalt 20V MAX Drill, Model DCD771C2 — now $99.00 (was $159.00)"},
        {"role": "assistant", "content": "DeWalt 20V MAX ड्रिल, मॉडल DCD771C2 — अभी $99.00 (पहले $159.00)"},
        {"role": "user", "content": "We couldn't process your payment. Please try a different card."},
        {"role": "assistant", "content": "हम आपका भुगतान प्रोसेस नहीं कर पाए। कृपया कोई दूसरा कार्ड आज़माएं।"},
    ],
}

_WRAPPING_QUOTES = "\"'“”‘’«»"


def _build_messages(text: str, target: str) -> tuple[str, list[dict]]:
    """Pure prompt assembly — unit-testable without a network call.

    Unknown targets get the generic translator prompt with no few-shot,
    so adding a language is data-only (open-closed)."""
    system = _BASE_SYSTEM.format(target=target) + _STYLE_BLOCKS.get(target, "")
    messages = [*_FEW_SHOT.get(target, []), {"role": "user", "content": text}]
    return system, messages


# Clients are created per call, not cached globally: an async HTTP client is
# bound to the event loop it was created on, and a cached one breaks with
# "Event loop is closed" outside a single long-lived loop. Connection setup
# is noise next to a 1-3 s LLM call.


async def _anthropic_call(model: str, system: str, messages: list[dict]) -> str:
    from anthropic import AsyncAnthropic  # lazy: provider SDKs load only when used

    async with AsyncAnthropic() as client:  # reads ANTHROPIC_API_KEY from the environment
        msg = await client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=messages,
        )
    return "".join(block.text for block in msg.content if block.type == "text")


async def _openrouter_call(model: str, system: str, messages: list[dict]) -> str:
    import httpx  # lazy, same policy as the anthropic import

    async with httpx.AsyncClient(
        base_url="https://openrouter.ai/api/v1",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        timeout=30.0,
    ) as client:
        resp = await client.post(
            "/chat/completions",
            json={
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "system", "content": system}, *messages],
            },
        )
    resp.raise_for_status()
    out = resp.json()["choices"][0]["message"]["content"]
    if not out or not out.strip():
        raise RuntimeError("OpenRouter returned an empty translation")
    return out


async def translate_text(text: str, target: str = "hi-IN", model: str | None = None) -> str:
    """Return `text` translated into `target` (Hindi by default).

    OpenRouter first when its key is set; Anthropic direct as fallback. The
    fallback is the ONLY caught failure — if Anthropic also fails, it raises.
    """
    system, messages = _build_messages(text, target)
    out = None
    if os.getenv("OPENROUTER_API_KEY"):
        try:
            out = await _openrouter_call(model or OPENROUTER_MODEL, system, messages)
        except Exception as exc:
            log.warning(
                "openrouter_failed_falling_back",
                extra={"error": f"{type(exc).__name__}: {exc}", "model": model or OPENROUTER_MODEL},
            )
    if out is None:
        # an explicit OpenRouter slug ("vendor/model") can't be sent to Anthropic
        anthropic_model = model if model and "/" not in model else ANTHROPIC_MODEL
        out = await _anthropic_call(anthropic_model, system, messages)
    return out.strip().strip(_WRAPPING_QUOTES).strip()
