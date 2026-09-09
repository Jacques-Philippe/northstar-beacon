# Beacon

An internal uptime monitor for the fictional company Northstar. It watches HTTP endpoints,
records the outcome of each probe, and reports current status, uptime, and incident history.

This file is the glossary — canonical terms only. No implementation detail. The domain
model and API live in `README.md`.

## Language

### Domain

**Monitor**:
The configured intent to watch one HTTP endpoint on a schedule.
_Avoid_: check, target, service, site, probe.

**CheckResult**:
The recorded outcome of one probe of a Monitor — reachable or not, status code, latency.
_Avoid_: ping, sample, hit, check.

**Incident**:
A period during which a Monitor is failing. Opens after a threshold of consecutive failed
CheckResults, closes on recovery.
_Avoid_: outage, downtime, alert, event.

**target** / **monitored endpoint**:
The external URL a Monitor watches.
_Avoid_: "service" — that word is reserved for the Kubernetes Service object.

**probe** (verb):
Beacon making an HTTP request to a monitored endpoint to produce a CheckResult.
For the Kubernetes concept, always write **"readiness probe"** or **"liveness probe"** in
full — never bare "probe". This collision is the main reason this glossary exists.

### Components

**api**:
The Beacon component that serves the HTTP API.
_Avoid_: server, backend, web.

**checker**:
The Beacon component that performs probes and opens/closes Incidents.
_Avoid_: worker, poller, scheduler, agent.

**frontend**:
The Beacon component that serves the browser UI — a Vue single-page app, built as its own
image and served by nginx. Reaches `api` through the Ingress.
_Avoid_: client, UI, web, dashboard (the *page* it renders can be called a dashboard; the
component is the frontend).

### Operations

**environment**:
One of `dev`, `staging`, `prod`. Each is its own kind cluster with its own database.
_Avoid_: stage, tier.

**Service**, **Deployment**, **StatefulSet** (capitalised):
Always the Kubernetes objects, never a generic sense.

**rollout**:
The act of shipping a new version of a Beacon component.
_Avoid_: "deployment" as a verb — that noun is a Kubernetes object.

**promotion**:
Moving an already-built, already-tested image from one environment to the next
(`dev` → `staging` → `prod`).
_Avoid_: redeploy, re-release.
