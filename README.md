# Beacon

A hands-on learning project built around a fictional internal application for a fictional
company (**Northstar**). Beacon is a lightweight **uptime monitor**: you register HTTP
endpoints, a background checker probes them on a schedule, and the API serves current
status, uptime percentages, and incident history.

The company, the application, and its requirements are all invented as a vehicle for
practice. The application is kept deliberately modest; the real subject is the **deployment
lifecycle** — Docker, Kubernetes, databases and stateful workloads, and CI/CD — and the
engineering judgement around them.

Beacon is a good vehicle because it *does something on its own*: it makes outbound network
calls that fail for real, and it naturally wants to be more than one running component.

## How this project runs

This is a **simulation of working on a real project over time**, not a tutorial or a fixed
spec. The developer is real (the learner). The rest of the project is roleplayed:

- **Marta** — Product Owner. Delivers requirements and priorities.
- Engineering manager, an infrastructure engineer, other developers, and users reporting
  problems, as the story needs them.

The requirements are **deliberately not settled up front**. Over the course of the project
the stakeholder will:

- introduce feature-changing requirements, sometimes after the relevant thing is already built
- give requirements that are ambiguous and need clarification
- change their mind, and re-prioritise

The domain model, API surface, and roadmap below are the **current** picture. They are
expected to move as feedback lands, and history (what changed, why, and what it cost) is
recorded in `docs/`. The learning is as much in absorbing changing requirements and
diagnosing the failures that follow as in the Kubernetes mechanics themselves.

## Learning objectives

- Architectural understanding of a deployed service
- The deployment lifecycle: source code → build artifact → image → container → Deployment → running Pod
- Reasoning about and diagnosing production failures (app bug vs. config error vs. database unavailable vs. the monitored target actually being down)
- Kubernetes primitives and *why* they exist — not `kubectl` syntax memorization
- Databases and stateful workloads, and how state changes the architecture
- CI/CD pipelines and rollout/rollback mechanics
- Tradeoffs, including when *not* to put a workload in Kubernetes

Mental model to keep returning to: **desired state → controllers → actual state**.

## Domain model

| Entity | Description | Key fields |
|--------|-------------|------------|
| **Monitor** | An HTTP endpoint Beacon watches. | `id`, `name`, `url`, `method`, `expected_status`, `interval_seconds`, `timeout_seconds`, `enabled`, `owning_team`, `created_at` |
| **CheckResult** | The outcome of one probe. Append-only, high-volume. | `id`, `monitor_id`, `checked_at`, `ok`, `status_code`, `response_ms`, `error` |
| **Incident** | Opens after N consecutive failing checks, closes on recovery. | `id`, `monitor_id`, `started_at`, `resolved_at`, `cause` (last error) |

Derived state:

- **Current status** of a monitor — from its latest `CheckResult` (`up` / `down`, and
  `degraded` if slow but passing).
- **Uptime %** over a window — computed from incidents (cheap) rather than scanning every result.

`CheckResult` is the row that grows without bound. Keeping it healthy — indexes on
`(monitor_id, checked_at)`, a retention policy, the migration that adds them — is the
concrete reason the database chapters matter.

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/monitors` | List monitors |
| POST   | `/monitors` | Register a monitor |
| GET    | `/monitors/{id}` | Monitor detail + current status |
| PATCH  | `/monitors/{id}` | Update a monitor |
| DELETE | `/monitors/{id}` | Remove a monitor |
| GET    | `/monitors/{id}/results` | Recent check results (`?since=`) |
| GET    | `/monitors/{id}/uptime` | Uptime % over a window (`?window=24h`) |
| GET    | `/incidents` | Incident history (`?monitor=&open=`) |
| GET    | `/incidents/{id}` | Incident detail |
| GET    | `/status` | Dashboard summary across all monitors |
| GET    | `/health/live` | Liveness — is the process up? |
| GET    | `/health/ready` | Readiness — can it serve traffic (e.g. DB reachable)? |

## Components

Beacon is two logical components whose separation is introduced *when the architecture
demands it*, not up front:

- **api** — the FastAPI service above.
- **checker** — a loop that finds monitors whose next check is due, probes them, writes
  `CheckResult`s, and opens/closes `Incident`s.

Progression:

1. The checker runs as a background task **inside the api process**. One process, in-memory
   data. Simple.
2. We want multiple `api` replicas for availability — but now every target gets probed once
   per replica. So the checker is split into **its own Deployment**.
3. Two processes now need **shared state** → this is what forces PostgreSQL, not a decree.
4. Later, running multiple `checker` replicas causes double-probing → a real
   stateful-coordination problem (`SELECT … FOR UPDATE SKIP LOCKED` / leader election),
   which is a more honest lesson than wrapping Postgres in a StatefulSet.

## Target architecture (built up gradually, not all at once)

- Python / FastAPI application, plus the checker worker
- PostgreSQL for persistent data
- Docker images with immutable tags (no reliance on `latest`)
- Docker Compose for local development
- Kubernetes for orchestration, with a local **kind** cluster
- Kubernetes objects introduced as they become relevant:
  Deployments, Services, ConfigMaps, Secrets, readiness/liveness probes,
  resource requests/limits, PVCs, and StatefulSets if the story calls for it
- GitHub Actions for CI/CD: tests → image build → push to registry → rollout → health checks → rollback
- A container registry for build artifacts

## Roadmap

1. FastAPI service, in-memory data, tests — Monitors + CheckResults, checker as an in-process background task
2. Incidents and the `/status` and `/uptime` endpoints
3. Containerize the api (Dockerfile)
4. Introduce PostgreSQL; Docker Compose for local dev; split the checker into its own process
5. Database migrations (Alembic)
6. Deploy to Kubernetes (kind): Deployments + Service for api and checker
7. Configuration via ConfigMaps and Secrets
8. Readiness/liveness probes and resource requests/limits
9. Persistent storage: decide whether PostgreSQL runs in-cluster or as a managed service
10. StatefulSets / PVCs if they earn their place
11. Multiple checker replicas and the double-probe coordination problem
12. CI/CD pipeline in GitHub Actions
13. Rolling deployments, then a deliberate rollback
14. Deliberate failures to diagnose (broken config, app bug causing 500s, broken readiness probe, DB unavailable)

## Tech stack

Python, FastAPI, pytest, PostgreSQL, Docker, Docker Compose, kind, kubectl, Kubernetes YAML, GitHub Actions.

Out of scope unless a concrete need arises: Redis, Kafka, microservices, cloud infrastructure, authentication.

## Status

Project scaffolding. No application code yet.

## Repository layout (planned)

```
app/                  FastAPI application code
app/checker/          the checker worker
tests/                pytest suite
Dockerfile
docker-compose.yml
k8s/                  Kubernetes manifests
.github/workflows/    CI/CD pipelines
docs/                 design notes and decisions
```
