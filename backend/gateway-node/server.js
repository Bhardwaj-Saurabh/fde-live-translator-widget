/*
 * FDE · Assignment 1 · Node Gateway  (the "software backend")
 * ==========================================================
 * This is the ONLY server the browser widget talks to. Its jobs:
 *   - serve the widget file at /widget.js
 *   - accept translation requests from the widget (CORS, validation)
 *   - forward them to the Python AI service
 *   - expose /health and /stats
 *   - log every request
 *
 * Fully implemented: request-ID tracing middleware, structured logging
 * (stdout + gateway.log), and the proxy to the Python AI service.
 *
 * Run:  npm install && npm start      (needs Node 18+ for global fetch)
 */
const express = require("express");
const cors = require("cors");
const path = require("path");
require("dotenv").config();

const PORT = process.env.PORT || 8787;
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || "http://localhost:8000";
const WIDGET_PATH = path.join(__dirname, "..", "..", "widget", "translation-widget.js");

const app = express();
const startedAt = Date.now();

// --- middleware ----------------------------------------------------------
app.use(cors()); // dev: allow every origin so the widget works on any page
app.use((req, res, next) => {
  // Chrome Private Network Access: public https pages fetching localhost
  // send a preflight that must be explicitly allowed.
  if (req.headers["access-control-request-private-network"]) {
    res.setHeader("Access-Control-Allow-Private-Network", "true");
  }
  next();
});
app.use(express.json({ limit: "1mb" }));

const crypto = require("node:crypto");
const fs = require("node:fs");

app.use((req, res, next) => {
  const t0 = Date.now();
  // trace correlation: reuse an inbound X-Request-Id, else generate one
  req.requestId = req.headers["x-request-id"] || crypto.randomUUID();
  res.setHeader("X-Request-Id", req.requestId);
  res.on("finish", () => {
    const line = JSON.stringify({
      ts: new Date().toISOString(),
      requestId: req.requestId,
      method: req.method,
      url: req.originalUrl,
      status: res.statusCode,
      durationMs: Date.now() - t0,
    });
    console.log(line);
    fs.appendFile("gateway.log", line + "\n", () => {});
  });
  next();
});

// --- serve the widget to the console loader ------------------------------
app.get("/widget.js", (req, res) => {
  res.type("application/javascript");
  res.sendFile(WIDGET_PATH);
});

// --- helper: forward a request to the Python AI service ------------------
async function callAiService(path, body, requestId) {
  const res = await fetch(AI_SERVICE_URL + path, {
    method: "POST",
    headers: { "content-type": "application/json", "x-request-id": requestId || "" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("AI service " + res.status);
  return res.json();
}

// --- routes the widget calls ---------------------------------------------
app.post("/translate", async (req, res) => {
  const { text, target } = req.body || {};
  if (typeof text !== "string") return res.status(400).json({ error: "`text` (string) is required" });
  try {
    const data = await callAiService("/translate", { text, target: target || "hi-IN" }, req.requestId);
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: "AI service error: " + err.message });
  }
});

app.post("/translate/batch", async (req, res) => {
  const { texts, target } = req.body || {};
  if (!Array.isArray(texts)) return res.status(400).json({ error: "`texts` (array) is required" });
  try {
    const data = await callAiService("/translate/batch", { texts, target: target || "hi-IN" }, req.requestId);
    res.json(data);
  } catch (err) {
    res.status(502).json({ error: "AI service error: " + err.message });
  }
});

app.get("/health", async (req, res) => {
  const uptimeSec = Math.round((Date.now() - startedAt) / 1000);
  let ai = "unreachable";
  try {
    const r = await fetch(AI_SERVICE_URL + "/health");
    ai = r.ok ? await r.json() : "error";
  } catch (_) {}
  res.json({ status: "ok", gatewayUptimeSec: uptimeSec, aiService: ai });
});

app.get("/stats", async (req, res) => {
  try {
    const r = await fetch(AI_SERVICE_URL + "/stats");
    res.json(await r.json());
  } catch (err) {
    res.status(502).json({ error: "AI service error: " + err.message });
  }
});

app.listen(PORT, () => {
  console.log(`FDE gateway on http://localhost:${PORT}  →  AI service ${AI_SERVICE_URL}`);
  console.log(`Widget served at http://localhost:${PORT}/widget.js`);
});
