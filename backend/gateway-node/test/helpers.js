/*
 * Test helpers: a stub AI service and a spawned gateway.
 *
 * server.js listens at require-time and exports nothing, so the honest way to
 * test it is as a real child process on a free port, pointed at a stub AI
 * service that records every request it receives. Zero test dependencies —
 * node:test, node:http, and global fetch only.
 */
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const { spawn } = require("node:child_process");

const GATEWAY_DIR = path.join(__dirname, "..");

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.listen(0, () => {
      const { port } = srv.address();
      srv.close((err) => (err ? reject(err) : resolve(port)));
    });
    srv.on("error", reject);
  });
}

/**
 * Stub AI service. Records {method, url, headers, body} of every request.
 * mode: "ok" (default) canned success responses · "fail500" every route 500s.
 */
async function startStubAiService({ mode = "ok" } = {}) {
  const requests = [];
  const server = http.createServer((req, res) => {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      let body = null;
      try { body = raw ? JSON.parse(raw) : null; } catch (_) {}
      requests.push({ method: req.method, url: req.url, headers: req.headers, body });

      if (mode === "fail500") {
        res.writeHead(500, { "content-type": "application/json" });
        return res.end(JSON.stringify({ error: "stub upstream failure" }));
      }

      if (req.url === "/clear-cache") {
        // mirrors the real AI service: bearer-token guarded admin endpoint
        if (req.headers.authorization !== "Bearer stub-admin-token") {
          res.writeHead(401, { "content-type": "application/json" });
          return res.end(JSON.stringify({ error: "invalid or missing admin token" }));
        }
        res.writeHead(200, { "content-type": "application/json" });
        return res.end(JSON.stringify({ cleared: { memory: 1, db: 2 } }));
      }

      const routes = {
        "/translate": { translated: "नमस्ते दुनिया", cached: false, latencyMs: 5, model: "stub-model" },
        "/translate/batch": {
          results: (body?.texts || []).map(() => ({ translated: "नमस्ते", cached: false })),
          latencyMs: 9,
        },
        "/health": { status: "ok", model: "stub-model", cacheSize: 1 },
        "/stats": { requests: 2, memory_hits: 1, db_hits: 0, misses: 1, hit_rate_pct: 50.0 },
      };
      const payload = routes[req.url];
      res.writeHead(payload ? 200 : 404, { "content-type": "application/json" });
      res.end(JSON.stringify(payload || { error: "not found" }));
    });
  });

  const port = await getFreePort();
  await new Promise((resolve) => server.listen(port, resolve));
  return {
    url: `http://localhost:${port}`,
    requests,
    stop: () => new Promise((resolve) => server.close(resolve)),
  };
}

/** Spawn server.js on a free port against `aiUrl`; resolves when /health answers.
 *  `env` merges extra variables into the child (e.g. RATE_LIMIT_MAX for limiter tests). */
async function startGateway({ aiUrl, env = {} }) {
  const port = await getFreePort();
  let stdout = "";
  const child = spawn(process.execPath, ["server.js"], {
    cwd: GATEWAY_DIR,
    env: { ...process.env, PORT: String(port), AI_SERVICE_URL: aiUrl, ...env },
  });
  child.stdout.on("data", (chunk) => (stdout += chunk));
  child.stderr.on("data", (chunk) => (stdout += chunk));

  const base = `http://localhost:${port}`;
  const deadline = Date.now() + 5000;
  for (;;) {
    try {
      const r = await fetch(`${base}/health`);
      if (r.ok) break;
    } catch (_) {}
    if (Date.now() > deadline) {
      child.kill();
      throw new Error(`gateway did not become healthy in 5s. Output:\n${stdout}`);
    }
    await new Promise((r) => setTimeout(r, 100));
  }

  return {
    base,
    port,
    stdout: () => stdout,
    stop: () => child.kill(),
  };
}

module.exports = { getFreePort, startStubAiService, startGateway };
