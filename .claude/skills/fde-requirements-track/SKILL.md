---
name: fde-requirements-track
description: Audit progress against the FDE Assignment 1 contract (AGENTS.md hard requirements + Definition of Done) and report a pass/fail/not-started checklist with concrete next actions. Use when the student asks "am I on track", "what's left", "check my requirements", or before recording the demo or submitting.
---

# FDE Live Translate — Requirements Tracker

Your job: report where the student stands against the assignment contract.
`AGENTS.md` is the contract — never relax, reinterpret, or skip a requirement.
This skill **reports only**; it does not fix anything. Every verdict needs
evidence from a command you actually ran — no verdicts from inspection alone.

## Step 0 — Read the contract
Read `AGENTS.md` and the Definition of Done in `README.md`, then load
`references/requirements-checklist.md` — it maps each hard requirement to the
exact command that verifies it and what PASS looks like.

## Step 1 — Static checks (work even when services are down)
1. **Progress map:** grep for `NotImplementedError` and `TODO (YOU)` in
   `backend/ai-service-python/app.py`, `lib/llm.py`, `lib/cache.py`, and
   `backend/gateway-node/server.js`. Anything still stubbed → NOT-STARTED.
2. **Red line — provided files untouched:**
   `git diff --stat -- widget extension loader demo-pages benchmark eval` must be empty.
3. **Hygiene:** `git status --porcelain` and `git ls-files` must show no
   `.env`, `*.db`, `*.log`, `node_modules/`, `.venv/`; grep backend source for
   hard-coded API keys (e.g. `sk-ant`).

## Step 2 — Live checks (only if both services answer)
Probe `curl -sf localhost:8000/health` and `curl -sf localhost:8787/health`.
If either is down, mark every live check **SKIPPED** (not FAIL) and tell the
student how to start the services. Otherwise run the checklist's live section:
- Contract shapes on `/translate`, `/translate/batch`, `/health` (nests
  `aiService`), `/stats` (contains a hit rate) — via the gateway.
- Cache proof: same `(text, target)` twice → 2nd has `cached: true` and a much
  lower `latencyMs`.
- `POST /translate` with bad input (`{"nope":1}`) → gateway returns `400`.
- Tracing: send a sentinel `X-Request-Id`, then grep it in BOTH `gateway.log`
  (or gateway stdout) and `backend/ai-service-python/ai-service.log`.
- A non-empty `*.db` exists under `backend/ai-service-python/`.

## Step 3 — SLA and deploy
- **Ask before running** `python benchmark/bench.py` (cache misses cost real
  LLM calls). Exit `0` = PASS; report which SLA failed otherwise.
- If a Fly.io gateway URL is known, `curl -sf https://<gateway>.fly.dev/health`;
  else mark deploy NOT-STARTED.

## Step 4 — Test-suite signal
If `backend/ai-service-python/tests/` exists, run `python -m pytest` there and
`npm test` in `backend/gateway-node/`, and fold pass/fail counts into the
report (red tests on unimplemented TODOs are expected — count them as
NOT-STARTED evidence, not failures of the suite).

## Step 5 — Report
One markdown table, grouped by the AGENTS.md sections (contract · LLM ·
caching · logging/tracing · SLA · deploy · hygiene):

| Requirement | Status | Evidence | Next action |

Status is PASS / FAIL / NOT-STARTED / SKIPPED. End with the **top 3 next
actions in build order** (cache → LLM → `translate_one` → gateway TODOs →
deploy). If any red-line check failed, put it first in bold.
