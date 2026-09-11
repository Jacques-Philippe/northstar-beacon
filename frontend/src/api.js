// Beat 2.2: a plain baked-in base URL from a build-time env var (Vite inlines
// `import.meta.env.VITE_API_URL` at build, not read at runtime). It only works because the
// two-port-forward setup happens to put `api` on the port this was built against — the
// fragility the Beat 2.3 Ingress removes by collapsing both to one origin.
const API_BASE = import.meta.env.VITE_API_URL ?? "";

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
