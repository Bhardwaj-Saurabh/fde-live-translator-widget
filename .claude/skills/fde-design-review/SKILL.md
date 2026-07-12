---
name: fde-design-review
description: Audit the student's backend code (backend/ai-service-python, backend/gateway-node) against system-design and SOLID principles adapted to this assignment, and report ranked findings with file:line evidence. Use when the student asks for a design review, architecture check, code review, or "is my code clean".
---

# FDE Live Translate — Design Review

**Scope guard (read first):** review ONLY `backend/ai-service-python/` and
`backend/gateway-node/`. NEVER suggest changes to `widget/`, `extension/`,
`loader/`, `demo-pages/`, `benchmark/`, or `eval/` — those are the provided
frontend and the grader. If a fix seems to require touching them, the real
finding is "the backend misreads the contract", and that is what you report.

This skill **reports only**. Do not edit files; apply fixes only if the
student explicitly asks afterwards.

## Step 1 — Read the code
Read `backend/ai-service-python/app.py`, `lib/llm.py`, `lib/cache.py`,
`lib/logger.py`, and `backend/gateway-node/server.js`. Note which TODOs still
raise `NotImplementedError` — principles that need code that doesn't exist yet
are reported as **"not reviewable yet"**, not as findings.

## Step 2 — Review against the six lenses
Detail and concrete anti-pattern snippets live in
`references/design-principles.md` — read it before judging.

1. **Single responsibility** — `app.py` does HTTP orchestration only;
   note: the prompt constants in `lib/llm.py` are distilled from
   `docs/hindi-style-guide.md`, not undocumented magic strings;
   `lib/llm.py` does the provider call only; `lib/cache.py` does storage only.
   Flag prompt-building or SQL in `app.py`, and HTTP shapes leaking into `lib/`.
2. **Dependency inversion / provider swappability** — `translate_text()` is
   the only LLM seam; keys come from `.env`; no provider SDK import outside
   `lib/llm.py`. Swapping Anthropic → Gemini must touch one file.
3. **Open-closed** — a new target language is data (the `target` param), zero
   code change; a new provider is an additive change inside `lib/llm.py`.
4. **Gateway vs AI-service separation** — the gateway owns edge concerns
   (CORS, validation → `400`, request-ID derivation, `502` mapping, widget
   serving); the AI service owns LLM + cache. No prompts in `server.js`, no
   CORS handling in `app.py`, browser never talks to `:8000`.
5. **Interface segregation of the cache** — callers use only
   `init/get/set/size/stats`; nothing outside `cache.py` touches `_mem` or
   `_stats`; SQLite details never leak upward.
6. **Fail-loud error propagation** — no `try/except` that returns the input
   English (the automatic-fail rule in AGENTS.md); `callAiService` throws on
   non-2xx so routes return `502`; exceptions never become a fake `200`.

## Step 3 — Bonus checks (report as suggestions, not violations)
- Single-flight dedup: concurrent identical requests should trigger one LLM call.
- No synchronous/blocking calls inside async paths (e.g. sync SDK in `async def`).
- aiosqlite connection handling: no leaked connections, sensible per-call usage.

## Step 4 — Report
Rank findings:
- **Critical** — violates an AGENTS.md hard requirement (e.g. silent English
  fallback, cache key not sha256, contract shape drift).
- **Major** — SOLID/separation violation that will hurt (provider SDK outside
  llm.py, gateway logic in the AI service).
- **Minor** — style, naming, small cleanups.

Each finding: `file:line` · one-line problem · one-line suggested refactor.
Close with a short **"done well"** list — this is a teaching review, not a
demolition.
