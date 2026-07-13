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
    "Preserve exactly as-is: numbers, prices and currency symbols ($ stays $ — never "
    "convert currencies or reformat numbers), percentages, product/model/SKU codes, "
    "brand names, units (GB, mAh, W), URLs, emails, HTML tags and entities, and emoji. "
    "If the input is a sentence fragment (a button label, heading, or menu item), "
    "translate it as a fragment — do not expand it into a sentence."
)

# Per-target style rules, distilled from docs/hindi-style-guide.md §2-§8.
# Adding a language = adding a dict entry here and in _FEW_SHOT; no code change.
_STYLE_BLOCKS: dict[str, str] = {
    "hi-IN": (
        "\n\nHindi style rules — write like popular Hindi blogs, news portals, and "
        "Amazon.in/Flipkart Hindi UIs, not like a formal translation:\n"
        "- Modern web Hindi in Devanagari script. NEVER romanized Hinglish output.\n"
        "- Address the reader as आप. Imperatives in the करें/-एं form (खरीदें, खोजें, "
        "जोड़ें, जारी रखें) — never कीजिए or करो.\n"
        "- Loanword pattern: keep common English NOUNS as Devanagari loanwords "
        "(कार्ट, चेकआउट, ऑर्डर, डिलीवरी, अकाउंट, प्रोडक्ट, स्टॉक, सेल, रेटिंग, ऐप, "
        "वेबसाइट, मोबाइल, बैटरी, ऑनलाइन); use native Hindi VERBS and value-words "
        "(खरीदें, खोजें, कीमत, छूट, भुगतान, समीक्षाएं, मदद, रद्द करें, चुनें).\n"
        "- NEVER use sanskritized coinages where a loanword is what people say: "
        "ऐप not अनुप्रयोग, इंटरनेट not अंतरजाल, कंप्यूटर not संगणक, कार्ट not टोकरी, "
        "खरीदें not क्रय करें.\n"
        "- Keep in Latin script: brand names (Home Depot, Google, DeWalt), model/SKU "
        "codes, acronyms (SEO, OTP, AI), units with numbers (1.5GB, 7200mAh).\n"
        "- Digits: Western 0-9 only, never Devanagari digits (१२३). Large numbers in "
        "prose use लाख/करोड़, never मिलियन.\n"
        "- Prose sentences end with the danda । (no space before, one after). "
        "UI fragments (buttons, labels, headings) get NO terminal punctuation.\n"
        "- Use canonical Indian e-commerce strings where they fit: Add to cart → "
        "कार्ट में जोड़ें, Buy now → अभी खरीदें, Free delivery → मुफ़्त डिलीवरी, "
        "Out of stock → स्टॉक में नहीं है, Track order → अपना ऑर्डर ट्रैक करें, "
        "Reviews → समीक्षाएं, Price → कीमत, Discount → छूट.\n"
        "- Restructure into natural Hindi word order (SOV); prefer two short "
        "sentences (~12-18 words) over one long mirrored one. Do not add "
        "conversational devices the source doesn't have."
    ),
}

# Few-shot as real user/assistant turns — the transcript itself teaches
# bare-input → bare-translation. Derived from the guide's §9 canonical pairs.
_FEW_SHOT: dict[str, list[dict]] = {
    "hi-IN": [
        {"role": "user", "content": "View all deals"},
        {"role": "assistant", "content": "सभी डील देखें"},
        {"role": "user", "content": "Free shipping on orders over $45"},
        {"role": "assistant", "content": "$45 से ज़्यादा के ऑर्डर पर मुफ़्त शिपिंग"},
        {"role": "user", "content": "DeWalt 20V MAX Drill, Model DCD771C2 — now $99.00 (was $159.00)"},
        {"role": "assistant", "content": "DeWalt 20V MAX ड्रिल, मॉडल DCD771C2 — अभी $99.00 (पहले $159.00)"},
        {"role": "user", "content": "Your package will arrive within 5 business days."},
        {"role": "assistant", "content": "आपका पैकेज 5 कारोबारी दिनों में पहुंच जाएगा।"},
        {"role": "user", "content": "We couldn't process your payment. Please try a different card."},
        {"role": "assistant", "content": "हम आपका भुगतान प्रोसेस नहीं कर पाए। कृपया कोई दूसरा कार्ड आज़माएं।"},
        {"role": "user", "content": "Sign in to see your saved items"},
        {"role": "assistant", "content": "अपने सेव किए आइटम देखने के लिए साइन इन करें"},
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
