"""
FDE · Assignment 1 · Python AI Service  (this is the real assignment)
=====================================================================
A small FastAPI service that translates English → Hindi with:
  - an LLM call            (lib/llm.py)
  - a two-tier cache       (lib/cache.py)  — memory + SQLite
  - structured logging     (lib/logger.py) — provided, wired for you

The Node gateway forwards the browser's requests here. You implement the
TODOs so the widget lights up. Run:

    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env          # then add your API key
    uvicorn app:app --reload --port 8000
"""
import asyncio
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from pydantic import BaseModel

from lib.cache import TwoTierCache
from lib.llm import translate_text
from lib.logger import get_logger

load_dotenv()

MODEL = os.getenv("MODEL", "claude-sonnet-4-6")
DB_PATH = os.getenv("TRANSLATION_DB_PATH", "translations.db")

app = FastAPI(title="FDE Live Translate — AI Service")
log = get_logger("ai-service")
cache = TwoTierCache(DB_PATH)

# request/response shapes ----------------------------------------------------
class TranslateIn(BaseModel):
    text: str
    target: str = "hi-IN"

class BatchIn(BaseModel):
    texts: list[str]
    target: str = "hi-IN"


@app.on_event("startup")
async def startup():
    await cache.init()
    log.info("ai_service_started", extra={"model": MODEL, "db": DB_PATH})


# --- core: translate one string --------------------------------------------
_inflight: dict[str, asyncio.Task] = {}


async def _translate_and_store(text: str, target: str) -> str:
    translated = await translate_text(text, target, model=MODEL)
    await cache.set(text, target, translated, model=MODEL)
    return translated


async def translate_one(text: str, target: str) -> dict:
    """Translate a single string, using the cache first.

    Returns a dict shaped exactly like the widget expects:
        {"translated": str, "cached": bool, "latencyMs": int, "model": str}
    """
    text = (text or "").strip()
    if not text:
        return {"translated": "", "cached": False, "latencyMs": 0, "model": MODEL}

    t0 = time.perf_counter()

    cached_value = await cache.get(text, target)
    if cached_value is not None:
        latency = int((time.perf_counter() - t0) * 1000)
        return {"translated": cached_value, "cached": True, "latencyMs": latency, "model": MODEL}

    # Single-flight: concurrent identical requests share one LLM call instead
    # of each paying for (and racing) their own. Waiters get the same result;
    # a failure propagates to all of them and nothing is cached.
    flight_key = f"{target}::{text}"
    task = _inflight.get(flight_key)
    if task is None:
        task = asyncio.create_task(_translate_and_store(text, target))
        _inflight[flight_key] = task
        task.add_done_callback(lambda _t: _inflight.pop(flight_key, None))
    translated = await task

    latency = int((time.perf_counter() - t0) * 1000)
    return {"translated": translated, "cached": False, "latencyMs": latency, "model": MODEL}


@app.post("/translate")
async def translate(body: TranslateIn, request: Request):
    result = await translate_one(body.text, body.target)
    log.info(
        "translate",
        extra={
            "requestId": request.headers.get("x-request-id"),
            "cached": result["cached"],
            "latencyMs": result["latencyMs"],
            "chars": len(body.text),
        },
    )
    return result


@app.post("/translate/batch")
async def translate_batch(body: BatchIn, request: Request):
    t0 = time.perf_counter()
    results = []
    for t in body.texts:
        results.append(await translate_one(t, body.target))
    latency = int((time.perf_counter() - t0) * 1000)
    hits = sum(1 for r in results if r["cached"])
    log.info(
        "translate_batch",
        extra={
            "requestId": request.headers.get("x-request-id"),
            "count": len(results),
            "hits": hits,
            "latencyMs": latency,
        },
    )
    # widget expects {results: [{translated, cached}], latencyMs}
    return {"results": [{"translated": r["translated"], "cached": r["cached"]} for r in results], "latencyMs": latency}


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL, "cacheSize": await cache.size()}


@app.get("/stats")
async def stats():
    return await cache.stats()
