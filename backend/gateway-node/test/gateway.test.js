/*
 * Gateway test suite — run with `npm test` (node --test).
 *
 * TDD note: the proxy, trace-ID, and request-logging tests stay RED until the
 * two `TODO (YOU)` blocks in server.js are implemented. The 400-validation,
 * /health, /stats, /widget.js, and 502-mapping tests should pass from day one.
 * Never weaken a test to make it pass — fix server.js (and only server.js).
 */
const { test, describe, before, after } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { startStubAiService, startGateway, getFreePort } = require("./helpers");

describe("gateway with a healthy AI service", () => {
  let stub, gw;
  before(async () => {
    stub = await startStubAiService();
    gw = await startGateway({ aiUrl: stub.url });
  });
  after(async () => {
    gw.stop();
    await stub.stop();
  });

  test("POST /translate proxies to the AI service and returns its JSON verbatim", async () => {
    const r = await fetch(`${gw.base}/translate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: "Hello world", target: "hi-IN" }),
    });
    assert.equal(r.status, 200);
    assert.deepEqual(await r.json(), {
      translated: "नमस्ते दुनिया",
      cached: false,
      latencyMs: 5,
      model: "stub-model",
    });
    const fwd = stub.requests.find((q) => q.url === "/translate");
    assert.ok(fwd, "gateway never called the AI service");
    assert.deepEqual(fwd.body, { text: "Hello world", target: "hi-IN" });
  });

  test("POST /translate defaults target to hi-IN", async () => {
    const countBefore = stub.requests.length;
    await fetch(`${gw.base}/translate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: "No target given" }),
    });
    const fwd = stub.requests.slice(countBefore).find((q) => q.url === "/translate");
    assert.equal(fwd?.body?.target, "hi-IN");
  });

  test("POST /translate/batch forwards the texts array and returns the batch shape", async () => {
    const r = await fetch(`${gw.base}/translate/batch`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ texts: ["Home", "Add to cart"], target: "hi-IN" }),
    });
    assert.equal(r.status, 200);
    const body = await r.json();
    assert.equal(body.results.length, 2);
    assert.equal(typeof body.latencyMs, "number");
    const fwd = stub.requests.find((q) => q.url === "/translate/batch");
    assert.deepEqual(fwd?.body?.texts, ["Home", "Add to cart"]);
  });

  test("returns exactly 400 when text is missing or not a string", async () => {
    for (const payload of [{}, { text: 123 }]) {
      const r = await fetch(`${gw.base}/translate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      assert.equal(r.status, 400, `expected 400 for ${JSON.stringify(payload)}`);
      assert.ok((await r.json()).error);
    }
  });

  test("returns exactly 400 when texts is not an array", async () => {
    const r = await fetch(`${gw.base}/translate/batch`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ texts: "not-an-array" }),
    });
    assert.equal(r.status, 400);
  });

  test("GET /health nests the live aiService payload", async () => {
    const body = await (await fetch(`${gw.base}/health`)).json();
    assert.equal(body.status, "ok");
    assert.notEqual(body.aiService, "unreachable");
    assert.equal(body.aiService?.status, "ok");
  });

  test("GET /stats passes through the AI service's hit rate", async () => {
    const body = await (await fetch(`${gw.base}/stats`)).json();
    assert.ok(Object.keys(body).some((k) => k.includes("hit_rate")));
  });

  test("GET /widget.js serves the widget with a JS content type", async () => {
    const r = await fetch(`${gw.base}/widget.js`);
    assert.equal(r.status, 200);
    assert.match(r.headers.get("content-type"), /javascript/);
    assert.ok((await r.text()).length > 0);
  });

  test("forwards an inbound X-Request-Id to the AI service", async () => {
    const sentinel = `trace-${Date.now()}-in`;
    await fetch(`${gw.base}/translate`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-request-id": sentinel },
      body: JSON.stringify({ text: "Trace me", target: "hi-IN" }),
    });
    const fwd = stub.requests.find((q) => q.headers["x-request-id"] === sentinel);
    assert.ok(fwd, "inbound X-Request-Id was not forwarded to the AI service");
  });

  test("generates an X-Request-Id when none is supplied", async () => {
    const countBefore = stub.requests.length;
    await fetch(`${gw.base}/translate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text: "Generate an id for me", target: "hi-IN" }),
    });
    const fwd = stub.requests.slice(countBefore).find((q) => q.url === "/translate");
    assert.ok(fwd, "gateway never called the AI service");
    assert.ok(fwd.headers["x-request-id"], "no x-request-id header was generated");
  });

  test("logs one structured line per request with method, url, status and duration", async () => {
    // A 400 request needs no AI service, so this isolates TODO #1 (logging).
    await fetch(`${gw.base}/translate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ nope: 1 }),
    });
    await new Promise((r) => setTimeout(r, 200)); // let res.on("finish") flush

    let logs = gw.stdout();
    const logFile = path.join(__dirname, "..", "gateway.log");
    if (fs.existsSync(logFile)) logs += fs.readFileSync(logFile, "utf8");

    const line = logs
      .split("\n")
      .find((l) => l.includes("/translate") && l.includes("400") && l.includes("POST"));
    assert.ok(line, "no request log line with method+url+status found — TODO #1");
    assert.match(line, /\d+\s?ms|"durationMs"|"duration"/, "log line has no duration");
  });
});

describe("gateway when the AI service fails", () => {
  test("returns 502 when the AI service responds 500 — and never echoes the English input", async () => {
    const stub = await startStubAiService({ mode: "fail500" });
    const gw = await startGateway({ aiUrl: stub.url });
    try {
      const input = "This must never come back as a translation";
      const r = await fetch(`${gw.base}/translate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: input, target: "hi-IN" }),
      });
      assert.equal(r.status, 502);
      const body = await r.json();
      assert.ok(body.error, "502 body must carry a JSON error");
      assert.notEqual(body.translated, input, "silent English fallback — automatic fail");
    } finally {
      gw.stop();
      await stub.stop();
    }
  });

  test("returns 502 when the AI service is unreachable", async () => {
    const deadPort = await getFreePort(); // nothing listening there
    const gw = await startGateway({ aiUrl: `http://localhost:${deadPort}` });
    try {
      const r = await fetch(`${gw.base}/translate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ text: "Anyone home?", target: "hi-IN" }),
      });
      assert.equal(r.status, 502);
    } finally {
      gw.stop();
    }
  });
});

describe("per-IP rate limiting", () => {
  function translate(base, text) {
    return fetch(`${base}/translate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text, target: "hi-IN" }),
    });
  }

  test("requests over the limit get 429 with Retry-After and RateLimit headers", async () => {
    const stub = await startStubAiService();
    const gw = await startGateway({
      aiUrl: stub.url,
      env: { RATE_LIMIT_MAX: "3", RATE_LIMIT_WINDOW_SEC: "60" },
    });
    try {
      for (let i = 0; i < 3; i++) {
        const r = await translate(gw.base, `under limit ${i}`);
        assert.equal(r.status, 200, `request ${i + 1} should pass`);
        assert.equal(r.headers.get("ratelimit-limit"), "3");
      }
      const blocked = await translate(gw.base, "over limit");
      assert.equal(blocked.status, 429);
      assert.ok(Number(blocked.headers.get("retry-after")) > 0, "Retry-After header missing");
      assert.equal(blocked.headers.get("ratelimit-remaining"), "0");
      const body = await blocked.json();
      assert.equal(body.error, "rate_limited");
      assert.equal(typeof body.retryAfterSec, "number");
    } finally {
      gw.stop();
      await stub.stop();
    }
  });

  test("health, stats, and widget.js are never rate limited", async () => {
    const stub = await startStubAiService();
    const gw = await startGateway({
      aiUrl: stub.url,
      env: { RATE_LIMIT_MAX: "1", RATE_LIMIT_WINDOW_SEC: "60" },
    });
    try {
      await translate(gw.base, "use up the only slot");
      assert.equal((await translate(gw.base, "blocked")).status, 429);
      for (const path of ["/health", "/stats", "/widget.js"]) {
        const r = await fetch(`${gw.base}${path}`);
        assert.equal(r.status, 200, `${path} must stay exempt from the limiter`);
      }
    } finally {
      gw.stop();
      await stub.stop();
    }
  });

  test("RATE_LIMIT_MAX=0 disables the limiter", async () => {
    const stub = await startStubAiService();
    const gw = await startGateway({
      aiUrl: stub.url,
      env: { RATE_LIMIT_MAX: "0", RATE_LIMIT_WINDOW_SEC: "60" },
    });
    try {
      for (let i = 0; i < 10; i++) {
        assert.equal((await translate(gw.base, `free ${i}`)).status, 200);
      }
    } finally {
      gw.stop();
      await stub.stop();
    }
  });

  test("batch larger than 100 texts is rejected with 400 before reaching the AI service", async () => {
    const stub = await startStubAiService();
    const gw = await startGateway({ aiUrl: stub.url });
    try {
      const r = await fetch(`${gw.base}/translate/batch`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ texts: Array.from({ length: 101 }, (_, i) => `t${i}`), target: "hi-IN" }),
      });
      assert.equal(r.status, 400);
      assert.ok((await r.json()).error);
      assert.ok(!stub.requests.some((q) => q.url === "/translate/batch"), "oversized batch must not be forwarded");
    } finally {
      gw.stop();
      await stub.stop();
    }
  });
});

describe("admin clear-cache relay", () => {
  let stub, gw;
  before(async () => {
    stub = await startStubAiService();
    gw = await startGateway({ aiUrl: stub.url });
  });
  after(async () => {
    gw.stop();
    await stub.stop();
  });

  test("forwards the Authorization header and mirrors 200 from the AI service", async () => {
    const r = await fetch(`${gw.base}/admin/clear-cache`, {
      method: "POST",
      headers: { authorization: "Bearer stub-admin-token" },
    });
    assert.equal(r.status, 200);
    assert.deepEqual(await r.json(), { cleared: { memory: 1, db: 2 } });
    const fwd = stub.requests.find((q) => q.url === "/clear-cache");
    assert.equal(fwd?.headers?.authorization, "Bearer stub-admin-token");
    assert.ok(fwd?.headers?.["x-request-id"], "request ID must be forwarded on admin calls too");
  });

  test("mirrors 401 (not 502) when the token is missing or wrong", async () => {
    const r = await fetch(`${gw.base}/admin/clear-cache`, { method: "POST" });
    assert.equal(r.status, 401);
    assert.ok((await r.json()).error);
  });
});
