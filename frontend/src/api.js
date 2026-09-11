// Beat 2.3: the Ingress puts the frontend and `api` on one origin, `api` reachable under
// the `/api` prefix. A relative path needs no per-environment config at all — no build-time
// URL, no CORS.
const API_BASE = "/api";

async function get(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${path} responded ${res.status}`);
  }
  return res.json();
}

export function getStatus() {
  return get("/status");
}

export function getMonitorUptime(monitorId) {
  return get(`/monitors/${monitorId}/uptime`);
}

export function getIncidents() {
  return get("/incidents");
}
