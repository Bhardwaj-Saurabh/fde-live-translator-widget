---
name: fde-test-suite
description: Run and maintain the 4-layer TDD test suite (eval-alignment, user-outcome, integration, edge-case) for the Live Translate backend and report a per-layer results table. Use when the student says "run the tests", "test my backend", or after implementing any backend TODO.
---

# FDE Live Translate — Test Suite

The suite is **TDD**: it was written before the backend TODOs, so red is
expected until they're built. A failure ending in `NotImplementedError` means
"not started", not "broken test". The layers:

| File | Layer | Predicts |
|---|---|---|
| `tests/test_eval_alignment.py` | contract & rubric mirror | `eval/eval.py` auto criteria |
| `tests/test_user_outcomes.py` | widget-user perspective | LLM & prompt-quality rubric rows |
| `tests/test_integration.py` | wiring + restart persistence | caching-correctness rubric row |
| `tests/test_edge_cases.py` | failure modes & odd input | fail-loud / automatic-fail rules |
| `backend/gateway-node/test/` | gateway contract, 400/502, tracing | service-separation + logging rows |

## Step 0 — Preconditions
- Python: a venv in `backend/ai-service-python/` with
  `pip install -r requirements.txt -r requirements-dev.txt`.
- Node: `npm install` done in `backend/gateway-node/`.
- **No services need to be running** — the Python suite runs the FastAPI app
  in-process with a mocked LLM; the Node suite spawns the gateway itself
  against a stub AI service on free ports.

## Step 1 — Run the Python suite
```bash
cd backend/ai-service-python && python -m pytest
```
The LLM is mocked; live tests are auto-excluded (`-m "not live"` in pytest.ini).

## Step 2 — Run the gateway suite
```bash
cd backend/gateway-node && npm test
```

## Step 3 — Optional live-LLM tests (ask first — real API cost, needs `.env` key)
```bash
cd backend/ai-service-python && RUN_LIVE_LLM_TESTS=1 python -m pytest -m live
```
These call the real `lib/llm.py` and are the only true check of es-MX register,
translation-only output, and price/SKU preservation.

## Step 4 — Report
A table: `Layer | Passed | Failed | What red means here`. For each failing
eval-alignment test, name the rubric criterion it predicts failing — the
mapping is in `references/test-map.md`. End with "implement next" guidance in
dependency order:
1. `lib/cache.py` (`init` → `get` → `set`)
2. `lib/llm.py` (`translate_text`)
3. `app.py` (`translate_one` cache→LLM→cache flow)
4. Gateway TODO #1 (logging middleware) and #2 (`callAiService` + request-ID forwarding)

## Step 5 — Maintenance rules (non-negotiable)
- **Never weaken, skip, or delete a test to make it pass** — fix the backend.
  If a test contradicts AGENTS.md, AGENTS.md wins; say so and fix the test to
  match the contract, never to match the code.
- Mock the LLM by default; any real-API test gets `@pytest.mark.live`.
- Every test database uses pytest's `tmp_path` — never the working
  `translations.db`.
- Never assert on internals of provided dirs (`widget/`, `extension/`, …).
- A new requirement gets a test in the matching layer file *before* the
  implementation; update `references/test-map.md` when tests are added.
