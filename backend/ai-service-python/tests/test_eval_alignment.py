"""Layer 1 — eval alignment.

Mirrors the auto criteria in eval/eval.py (rubric.json): passing here predicts
passing the scored rubric. Each test names the criterion it protects — see
.claude/skills/fde-test-suite/references/test-map.md.
"""
import uuid

from conftest import AI_SERVICE_LOG, translate


# rubric: widget_lights_up — /translate contract shape
async def test_translate_response_has_contract_keys(client):
    r = await translate(client, "Good morning, welcome!")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["translated"], str) and body["translated"]
    assert isinstance(body["cached"], bool)
    assert isinstance(body["latencyMs"], int)
    assert isinstance(body["model"], str)


# rubric: widget_lights_up — /translate/batch contract shape
async def test_batch_response_shape(client):
    texts = ["Home", "Add to cart"]
    r = await client.post("/translate/batch", json={"texts": texts, "target": "es-MX"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["latencyMs"], int)
    assert len(body["results"]) == len(texts)
    for item in body["results"]:
        assert set(item) == {"translated", "cached"}


async def test_health_reports_status_ok_model_cachesize(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert isinstance(body["model"], str)
    assert isinstance(body["cacheSize"], int)


# rubric: logging_observability — /stats must expose a hit rate
async def test_stats_exposes_hit_rate(client):
    r = await client.get("/stats")
    assert r.status_code == 200
    assert any("hit_rate" in key for key in r.json())


# rubric: caching_correctness — 2nd identical call is a cache hit, faster,
# and the LLM is called exactly once
async def test_second_identical_call_cached_true_and_faster(client, fake_llm):
    fake_llm.delay = 0.05
    first = (await translate(client, "Best sellers")).json()
    second = (await translate(client, "Best sellers")).json()
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["translated"] == first["translated"]
    assert second["latencyMs"] <= first["latencyMs"]
    assert len(fake_llm.calls) == 1


# rubric: caching_correctness — a non-empty SQLite file must exist
async def test_sqlite_db_file_exists_and_nonempty_after_set(client, db_path):
    await translate(client, "Free shipping on orders over $45")
    assert db_path.exists()
    assert db_path.stat().st_size > 0


# rubric: service_separation_contract — bad input is rejected.
# FastAPI/pydantic answers 422; the eval's exact-400 check targets the
# gateway, which is asserted in backend/gateway-node/test/gateway.test.js.
async def test_invalid_body_rejected_4xx(client):
    r = await client.post("/translate", json={"nope": 1})
    assert 400 <= r.status_code < 500


# rubric: logging_observability — trace correlation. The gateway forwards
# x-request-id; the AI service must log it on the translation line.
# RED until the student wires the header into the log call in app.py.
async def test_request_id_appears_in_ai_service_log(client):
    sentinel = f"evaltest-{uuid.uuid4()}"
    r = await translate(client, "Track my order", headers={"x-request-id": sentinel})
    assert r.status_code == 200
    assert AI_SERVICE_LOG.exists(), "ai-service.log was not written"
    assert sentinel in AI_SERVICE_LOG.read_text(), (
        "x-request-id not logged — forward it into log.info(..., extra={...}) in app.py"
    )
