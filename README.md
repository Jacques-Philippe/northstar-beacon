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

- **Michael** — Product Owner. Delivers requirements and priorities.
- Engineering manager, an infrastructure engineer, other developers, and users reporting
  problems, as the story needs them.

The requirements are **deliberately not settled up front**. Over the course of the project
the stakeholder will:

- introduce feature-changing requirements, sometimes after the relevant thing is already built
- change their mind, and re-prioritise

The domain model, API surface, and roadmap below are the **current** picture. They are
expected to move as feedback lands, and history (what changed, why, and what it cost) is
recorded in `docs/`. The full planned arc lives in `docs/narrative.md`. The learning is as
much in absorbing changing requirements and diagnosing the failures that follow as in the
Kubernetes mechanics themselves.

## Working practices

The project is run the way a real one would be:

- It lives in a **public GitHub repository**.
- Every requirement, feature, and reported failure is tracked as a **GitHub issue**, opened
  before implementation starts.
- Changes land through **pull requests** — one per issue — that close the issue they
  address. No direct commits to the default branch.
- A **full GitHub Actions CI/CD pipeline is a committed deliverable**: tests on every PR,
  image build tagged with the immutable git SHA, push to a container registry (GHCR),
  manifest update, rollout to the cluster, and a working rollback path. It is built up over
  the roadmap but its completion is not optional.

See `CLAUDE.md` for the conventions in detail.

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

Beacon is two logical components. They start fused and separate *when the architecture
demands it*, not up front:

- **api** — the FastAPI service above.
- **checker** — a loop that finds monitors whose next check is due, probes them, writes
  `CheckResult`s, and opens/closes `Incident`s.

Progression:

1. The checker runs as a background task **inside the api process** — one process,
   in-memory data. This is what gets containerised and deployed to kind first.
2. History (uptime, incidents) is added; a rollout or a rescheduled Pod wipes it, because
   **Pods are ephemeral** → this forces PostgreSQL, for durability, not by decree.
3. `api` is scaled to multiple replicas for availability — but now every target is probed
   once per replica → the checker is split into **its own Deployment**.
4. The single checker can't keep up → running multiple `checker` replicas causes
   double-probing → a real stateful-coordination problem
   (`SELECT … FOR UPDATE SKIP LOCKED` / leader election), a more honest lesson than
   wrapping Postgres in a StatefulSet.

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

The organising idea is **into the cluster fast**: a deliberately trivial version is running
on kind by step 3, and everything after that is layered onto an app that is already
deployed. See `docs/narrative.md` for the beat-by-beat story.

**Act 1 — Into the cluster**
1. Minimal FastAPI service: Monitor CRUD, in-memory, in-process checker, `/health/*` stubs, tests
2. Containerize it (Dockerfile, immutable git-SHA tags, no `latest`)
3. Deploy to kind: Deployment + Service, the `kubectl get/describe/logs` loop
4. Make the deploy loop routine: ship a small change end-to-end (edit → build → load → apply → rollout)

**Act 2 — State forces the architecture**
5. Add history: CheckResults, Incidents, `/uptime`, `/status`
6. Feel Pod ephemerality: a rollout wipes in-memory history
7. Introduce PostgreSQL (Compose for local dev; naive `emptyDir` Deployment in-cluster for now)
8. Move config out of the image: ConfigMaps and Secrets
9. Database migrations (Alembic), and how they run relative to a rollout

**Act 3 — Running it properly**
10. Readiness vs. liveness probes
11. Resource requests and limits
12. Scale the api; split the checker into its own Deployment
13. Decision: should PostgreSQL run in-cluster or be managed?
14. StatefulSet + PVC for PostgreSQL
15. Multiple checker replicas and the double-probe coordination problem

**Act 4 — CI/CD and the failure gauntlet**
16. CI/CD pipeline in GitHub Actions (test → build → push to registry → rollout)
17. Rolling deployment of a real feature, then a deliberate rollback
18. The failure gauntlet: app bug (500s), broken readiness probe, DB unavailable, stale-replica skew

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
