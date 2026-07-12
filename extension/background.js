/*
 * FDE · Assignment 1 · Extension background worker
 * ------------------------------------------------
 * Relays the widget's API calls out of the page context. Content-script
 * fetches are subject to the host page's CSP, CORS, and Chrome's
 * private-network-access rules — which is exactly what blocks a direct
 * call to http://localhost:8787 from a strict site like homedepot.com.
 * Fetches made HERE run with the extension's host_permissions and are
 * exempt from all three.
 */
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || msg.type !== "FDE_FETCH") return;
  chrome.storage.sync.get({ apiUrl: "http://localhost:8787" }, async (cfg) => {
    try {
      const res = await fetch(cfg.apiUrl + msg.path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(msg.body),
      });
      const data = await res.json().catch(() => null);
      sendResponse({ ok: res.ok, status: res.status, data });
    } catch (err) {
      sendResponse({ ok: false, status: 0, error: String((err && err.message) || err) });
    }
  });
  return true; // keep the message channel open for the async sendResponse
});
