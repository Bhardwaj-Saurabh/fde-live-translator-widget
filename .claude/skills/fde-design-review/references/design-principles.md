# Design principles for this assignment — what good and bad look like

Each lens below is SOLID/system design translated into this codebase's shape.
The snippets are illustrative anti-patterns to recognize, not code to paste.

## 1. Single responsibility

Each module has one reason to change:
- `app.py` — HTTP shapes, endpoint wiring, the cache→LLM→cache orchestration.
- `lib/llm.py` — prompt + provider call. Changing the prompt touches only this file.
- `lib/cache.py` — storage tiers and stats. Changing SQLite schema touches only this file.
- `lib/logger.py` — log formatting (provided).

**Anti-pattern:** building the translation prompt inside `translate_one()`:

```python
# BAD — app.py now changes when the prompt changes
async def translate_one(text, target):
    system = "You are a professional translator. Translate into Hindi…"
    msg = await client.messages.create(system=system, ...)
```

## 2. Dependency inversion / provider swappability

`app.py` depends on the abstraction `translate_text(text, target, model)`, not
on a vendor SDK. The provider SDK is imported only inside `lib/llm.py`; the key
comes from `.env`.

**Anti-pattern:** `from anthropic import AsyncAnthropic` at the top of
`app.py`, or `client = AsyncAnthropic(api_key="sk-ant-…")` anywhere (hard-coded
key = hygiene fail too).

**Good sign:** switching Anthropic → Gemini is a diff confined to `lib/llm.py`
plus `.env` values.

## 3. Open-closed

- New target language: pass a different `target` — the cache key already
  includes it, the prompt should interpolate it. Zero structural change.
- New provider: add a branch/implementation in `lib/llm.py` selected by env
  (e.g. `LLM_PROVIDER`), without editing `app.py` or the cache.

**Anti-pattern:** `if target == "hi-IN": … elif target == "es-ES": …` chains in
`app.py`, or per-language endpoints.

## 4. Gateway vs AI-service separation

| Concern | Lives in |
|---|---|
| CORS, body validation → `400`, rate limiting | gateway (`server.js`) |
| Request-ID derivation + forwarding (`x-request-id`) | gateway (AI service only logs it) |
| Mapping upstream failure → `502` | gateway |
| Serving `/widget.js` | gateway |
| Prompt, model choice, provider key | AI service (`lib/llm.py`) |
| Cache tiers + stats | AI service (`lib/cache.py`) |

**Anti-patterns:** the gateway calling the LLM provider directly; the AI
service doing CORS; the browser configured to hit `:8000`; the gateway
re-implementing `latencyMs` measurement instead of passing the AI service's
response through.

## 5. Interface segregation of the cache

Callers see `init() / get(text, target) / set(text, target, translated, model)
/ size() / stats()` — nothing else.

**Anti-patterns:**
- `app.py` reading `cache._mem` or mutating `cache._stats` directly.
- `app.py` opening `aiosqlite.connect(...)` itself.
- `get()` returning SQLite row tuples instead of the translated string.

## 6. Fail-loud error propagation (automatic-fail rule)

The one bug this assignment is designed to catch:

```python
# AUTOMATIC FAIL — silently serves English while looking healthy
try:
    translated = await translate_text(text, target)
except Exception:
    translated = text   # ← never do this
```

Correct behavior: let the exception propagate (optionally log it), FastAPI
returns 5xx, the gateway maps it to `502`, the widget shows an error. Same on
the gateway: `callAiService` throws on non-2xx; routes catch and return `502`
with a JSON error body — never a fabricated success.

Also check: a failed LLM call must not be written to the cache, and the
response must never claim `cached: true` for it.

## Bonus: single-flight dedup

"Identical `(text, target)` MUST NOT call the LLM twice" also applies to
*concurrent* identical requests (a page full of repeated strings arrives in a
burst). A per-key map of pending futures/promises in `translate_one()` (or the
cache) makes the second concurrent caller await the first's LLM call instead
of issuing its own.
