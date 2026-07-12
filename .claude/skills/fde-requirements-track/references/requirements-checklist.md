# Requirements checklist — requirement → verification → PASS looks like

Source of truth: `AGENTS.md`. Run the command; judge only on its output.

## Contract

| Requirement | Verify with | PASS looks like |
|---|---|---|
| `POST /translate` shape | `curl -s localhost:8787/translate -H 'content-type: application/json' -d '{"text":"Good morning","target":"hi-IN"}'` | 200 with keys `translated` (str), `cached` (bool), `latencyMs` (num), `model` (str) |
| `POST /translate/batch` shape | `curl -s localhost:8787/translate/batch -H 'content-type: application/json' -d '{"texts":["Home","Add to cart"],"target":"hi-IN"}'` | 200 with `results: [{translated, cached}, …]` (same length/order) and `latencyMs` |
| `GET /health` | `curl -s localhost:8787/health` | `status: "ok"` and a nested `aiService` object (not `"unreachable"`) |
| `GET /stats` | `curl -s localhost:8787/stats` | cache counters including a `hit_rate` field |
| 400 on bad input | `curl -s -o /dev/null -w '%{http_code}' localhost:8787/translate -H 'content-type: application/json' -d '{"nope":1}'` | `400` |
| 502 on upstream failure | stop the AI service, repeat a translate call | `502` with a JSON error body |
| Widget unmodified | `git diff --stat -- widget extension loader demo-pages benchmark eval` | empty output (red line if not) |

## LLM

| Requirement | Verify with | PASS looks like |
|---|---|---|
| hi-IN, translation only | translate `"Good morning, welcome!"` and 2–3 more | natural Hindi, no preamble/quotes |
| Numbers/prices/codes preserved | translate `"Now $1,299.00 — model WH-1000XM5, save 25%"` | `$1,299.00`, `WH-1000XM5`, `25%` verbatim in output |
| Key from env, provider swappable | grep backend source for literal keys; check `.env.example` | no hard-coded keys; provider config via env |
| Fail loud, never silent English | grep `lib/llm.py` / `app.py` for `try`/`except` returning the input | no fallback returning `text`; provider errors propagate → gateway `502` |

## Caching

| Requirement | Verify with | PASS looks like |
|---|---|---|
| Identical input never hits LLM twice | same translate call twice; check AI-service log | 2nd response `cached: true`; only one LLM/translate-miss log line |
| Hit dramatically faster | compare `latencyMs` of the two calls | hit is orders of magnitude lower (ms vs seconds) |
| SQLite tier survives restart | restart the AI service, repeat the call | still `cached: true` |
| Two tiers + SHA-256 key | read `lib/cache.py` | memory dict + SQLite; `_key` = sha256 of `(target, text)` |
| Non-empty DB file | `ls -la backend/ai-service-python/*.db` | file exists, size > 0 |

## Logging & tracing

| Requirement | Verify with | PASS looks like |
|---|---|---|
| Gateway line per request | make a request, check gateway stdout/`gateway.log` | one structured line: method, url, status, duration ms |
| AI line per translation | check `backend/ai-service-python/ai-service.log` | one JSON line per translation: cached, latencyMs, chars |
| Trace correlation | `curl -s localhost:8787/translate -H 'content-type: application/json' -H 'X-Request-Id: trace-check-123' -d '{"text":"Hello","target":"hi-IN"}'` then `grep trace-check-123` in both logs | the id appears in BOTH gateway and AI-service logs |

## SLA, deploy, hygiene

| Requirement | Verify with | PASS looks like |
|---|---|---|
| SLA gate | `python benchmark/bench.py` (ask first — costs LLM calls) | exit code `0` |
| One-command local run | read the two backend READMEs / package.json | `npm start` and `uvicorn app:app --port 8000` documented and working |
| Fly.io deploy | `curl -sf https://<gateway-app>.fly.dev/health` | 200 `status: "ok"` |
| Hygiene | `git ls-files \| grep -E '\.env$\|\.db$\|\.log$\|node_modules\|\.venv'` | no output |
