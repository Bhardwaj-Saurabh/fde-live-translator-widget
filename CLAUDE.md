# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

FDE Assignment 1 — Live Translate. A provided browser widget translates English web pages into **Mexican Spanish (es-MX)**; the student builds the two backend services that power it. **`AGENTS.md` is the binding contract for this assignment — read it before changing anything.** `README.md` has the full brief, grading rubric, and troubleshooting.

## Boundaries — what to touch

- **BUILD:** `backend/ai-service-python/` (LLM call, two-tier cache, logging — the core work) and `backend/gateway-node/` (two `TODO (YOU)` blocks in `server.js`: request-logging middleware + `callAiService()` proxy).
- **NEVER EDIT:** `widget/`, `loader/`, `extension/`, `demo-pages/`, `benchmark/`, `eval/`. These are the provided frontend and the grader; the eval auto-flags edits to them as red-line failures. If a fix seems to require editing them, the contract has been misread.

## Architecture

Three parts, JSON over HTTP:

```
Browser widget/extension → Node gateway :8787 → Python AI service :8000 → LLM + SQLite cache
```

- **Node gateway** (`backend/gateway-node/server.js`, Express): the only thing the browser talks to. CORS, validation, request logging, serves `/widget.js`, proxies `/translate`, `/translate/batch`, `/health`, `/stats` to the AI service. Returns `400` on bad input, `502` on upstream failure.
- **Python AI service** (`backend/ai-service-python/`, FastAPI): `app.py` wires the cache→LLM→cache flow in `translate_one()`; `lib/llm.py` holds the prompt + provider call (provider swappable via env, key from `.env`); `lib/cache.py` is the two-tier cache — in-memory dict in front of SQLite (`translations.db`), key = SHA-256 of `(target::text)`; `lib/logger.py` (provided) emits structured log lines.
- **Tracing:** the gateway derives a request ID per request (reuse inbound `X-Request-Id` or generate), forwards it as `x-request-id`, and both services log it — one request must be greppable across both logs by that ID.

The API contract (shapes in README/AGENTS.md) is fixed — the provided widget must work unmodified against the gateway.

## Non-negotiable behaviors

- **Fail loud on LLM errors:** never catch a provider failure and return the original English as if translated — that is an automatic fail. Let it propagate so the gateway returns `502`.
- **Cache correctness:** identical `(text, target)` never calls the LLM twice; `cached: true` only when served from cache; the SQLite tier must survive a restart; `latencyMs` is measured server-side on both paths.
- **LLM output:** natural es-MX (not Castilian), translation only (no preamble/quotes), numbers/prices/product codes preserved verbatim.

## Commands

```bash
# AI service (build/test this first — no browser needed)
cd backend/ai-service-python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                      # add API key
uvicorn app:app --reload --port 8000

# Gateway
cd backend/gateway-node
npm install && cp .env.example .env
npm start                                 # http://localhost:8787

# Smoke test (run twice — 2nd must be "cached": true with far lower latencyMs)
curl -s localhost:8787/translate -H 'content-type: application/json' \
  -d '{"text":"Good morning","target":"es-MX"}'

# SLA benchmark — the grading gate; must exit 0 (targets in benchmark/sla.json)
python benchmark/bench.py                 # through the gateway
python benchmark/bench.py --direct        # straight to the AI service

# Score the rubric / generate the submission report
python eval/eval.py --student "Name" --video "https://…"   # writes eval/REPORT.md
# or run the /fde-live-translate-eval skill → writes PRODUCT_EVAL.md (the deliverable)
```

There is no separate test suite — `benchmark/bench.py` (SLA gate) and `eval/eval.py` (rubric) are the verification. The full self-verify checklist (cache-restart proof, trace-ID grep across both logs, hygiene) is in AGENTS.md; run it before claiming done.

## Deploy

Both services ship to Fly.io (`fly launch` → `fly secrets set …` → `fly deploy`, one app per backend dir); the extension popup points at the public gateway URL. Keep the AI service private (flycast) so only the gateway reaches it. The live-website test must pass against the deployed gateway, not localhost.

## Hygiene

Never commit `.env`, `node_modules/`, `.venv/`, `*.db`, or `*.log`. If the widget is changed for any reason (it shouldn't be), the extension carries its own copy: `cp widget/translation-widget.js extension/`.
