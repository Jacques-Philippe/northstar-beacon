---
Status: accepted
Date: 2026-09-09
---

# 0002. Beacon (an uptime monitor) as the learning vehicle

The project needs a small application to carry the real subject — the deployment lifecycle.
We chose an **uptime monitor**: you register HTTP endpoints, a background checker probes
them on a schedule, and an API serves current status, uptime, and incident history.

## Considered options

- **Deployment tracker** (the original brief) — rejected: pure CRUD, no behaviour of its
  own, so every failure to diagnose has to be injected artificially.
- **URL shortener** — rejected: single component, and the redirect-path story is thin for
  Kubernetes lessons.
- **Feature-flag service** — rejected: middling fit, no strong multi-component pull.
- **Uptime monitor** — chosen: it makes outbound network calls that fail for real, and it
  naturally wants to be more than one running component (api + checker), which makes the
  multi-workload and stateful-coordination lessons fall out of the domain instead of being
  staged.

## Consequences

Everything downstream — the two-component split, the DB, the checker-coordination beat —
assumes this domain.
