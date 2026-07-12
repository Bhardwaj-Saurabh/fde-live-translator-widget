"""Shared fixtures for the AI-service test suite.

The FastAPI app runs in-process via httpx's ASGITransport — no uvicorn, no
network. The LLM is replaced with FakeLLM (deterministic, records calls) and
every test gets its own TwoTierCache on a tmp_path SQLite file, swapped into
the app module.

ASGITransport does NOT fire FastAPI startup events, so the cache fixture
calls init() itself instead of relying on app.startup().
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))
# app.py and lib/logger.py have import-time side effects (module-level cache,
# ai-service.log created in the cwd). Pin the cwd to the service dir so those
# land next to the code (where they're gitignored) no matter where pytest is
# invoked from, and keep the module-level cache off the real translations.db.
os.chdir(SERVICE_DIR)
os.environ.setdefault("TRANSLATION_DB_PATH", str(SERVICE_DIR / ".pytest-import-side-effect.db"))

import app as app_module  # noqa: E402
import lib.llm as llm_module  # noqa: E402
from lib.cache import TwoTierCache  # noqa: E402
from lib.logger import LOG_FILE  # noqa: E402

import httpx  # noqa: E402

AI_SERVICE_LOG = SERVICE_DIR / LOG_FILE


class FakeLLM:
    """Stands in for lib.llm.translate_text.

    Returns "[<target>] <text>" — deterministic and verbatim-preserving, so
    tests can assert prices/SKUs survive the round trip. Records every call;
    `delay` simulates provider latency, `fail` makes the call raise.
    """

    def __init__(self):
        self.calls: list[tuple[str, str]] = []
        self.delay: float = 0.0
        self.fail: Exception | None = None

    async def __call__(self, text: str, target: str = "hi-IN", model: str = "fake-model") -> str:
        self.calls.append((text, target))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail is not None:
            raise self.fail
        return f"[{target}] {text}"


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    # app.py does `from lib.llm import translate_text`, so the binding that
    # matters is the one in the app module — patch both to be safe.
    monkeypatch.setattr(app_module, "translate_text", fake)
    monkeypatch.setattr(llm_module, "translate_text", fake)
    return fake


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test-translations.db"


@pytest.fixture
async def test_cache(monkeypatch, db_path):
    cache = TwoTierCache(str(db_path))
    try:
        await cache.init()
    except NotImplementedError:
        # TDD: cache.init() is a student TODO. Swallowing it HERE keeps the
        # fixture from erroring so each test fails on the code it actually
        # exercises (a clean "not built yet" signal, not a broken suite).
        pass
    monkeypatch.setattr(app_module, "cache", cache)
    return cache


@pytest.fixture
async def client(fake_llm, test_cache):
    transport = httpx.ASGITransport(app=app_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def client_no_raise(fake_llm, test_cache):
    """Client whose transport turns unhandled app exceptions into 500s
    instead of propagating into the test — needed for fail-loud tests."""
    transport = httpx.ASGITransport(app=app_module.app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def translate(client, text, target="hi-IN", **kwargs):
    payload = {"text": text}
    if target is not None:
        payload["target"] = target
    return await client.post("/translate", json=payload, **kwargs)
