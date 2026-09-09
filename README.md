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

The domain model and API surface below are the **current** picture. They are
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
- There are **three environments** — `dev`, `staging`, `prod` — each its own local **kind**
  cluster, configured with kustomize overlays. Everything runs locally: **zero cloud spend**
  (ADR-0003).
- Settled design decisions are recorded in **`docs/adr/`**; domain vocabulary in
  **`CONTEXT.md`**.

See `CLAUDE.md` for the conventions in detail, and `docs/adr/` for the reasoning behind the
architecture.

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
| **Monitor** | An HTTP endpoint Beacon watches. | `id`, `name`, `url`, `method`, `expected_status`, `interval_seconds`, `timeout_seconds`, `enabled`, `created_at` |
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

Beacon is two logical components:

- **api** — the FastAPI service above.
- **checker** — a loop that finds monitors whose next check is due, probes them, writes
  `CheckResult`s, and opens/closes `Incident`s.

They start fused: the checker runs as a background task **inside the api process**, on
in-memory data — that is what gets containerised and deployed to kind first. How and when
they come apart — the checker into its own Deployment, then multiple checker replicas with a
real stateful-coordination problem (`SELECT … FOR UPDATE SKIP LOCKED` / leader election) —
is driven by specific beats in `docs/narrative.md`, not decided up front.

## Target architecture (built up gradually, not all at once)

- Python 3.12 / FastAPI application, plus the checker worker; `uv` + `pyproject.toml`
- One container image, two entrypoints (`api` / `checker`); immutable git-SHA tags
- PostgreSQL for persistent data, via a `Storage` interface (SQLAlchemy 2.0 ORM + Alembic)
- Docker Compose for the local dev database
- Kubernetes for orchestration: three local **kind** clusters (`dev` / `staging` / `prod`)
- Kubernetes objects introduced as they become relevant:
  Deployments, Services, ConfigMaps, Secrets, readiness/liveness probes,
  resource requests/limits, PVCs, StatefulSets, Jobs
- kustomize `base/` + `overlays/{dev,staging,prod}/` for per-environment config
- GitHub Actions for CI/CD: tests → image build → push to GHCR → deploy to dev → gated
  promotion to staging and prod → rollback
- Prometheus `/metrics` endpoint (no Prometheus/Grafana deployment)

## The arc

The organising idea is **into the cluster fast**: a deliberately trivial version is running
on kind by Beat 1.3, and everything after that is layered onto an app that is already
deployed. Acts 1–3 run against a single `beacon-dev` cluster; the other two environments and
the promotion pipeline arrive in Act 4.

- **Act 1 — Into the cluster.** Minimal service → containerise → deploy to kind → make the
  deploy loop routine.
- **Act 2 — State forces the architecture.** Add history → feel Pod ephemerality → introduce
  PostgreSQL → move config out of the image → database migrations.
- **Act 3 — Running it properly.** Readiness vs. liveness → resource requests and limits →
  scale the api and split out the checker → the managed-vs-in-cluster database decision →
  StatefulSet + PVC → multiple checker replicas and coordination → a metrics endpoint.
- **Act 4 — CI/CD, multiple environments, and the failure gauntlet.** Build the pipeline →
  stand up staging and prod → ship a feature dev → staging → prod, then roll back → the
  diagnosis gauntlet.

`docs/narrative.md` is the **roadmap of record**: the full beat-by-beat script, with each
beat's trigger, build, complication, and lesson; it is amended in place as beats are
played. What actually happened is the git history, the merged PRs, and the closed issues.

## Tech stack

Python 3.12, `uv`, FastAPI, pytest, SQLAlchemy 2.0 + Alembic, PostgreSQL, Docker, Docker
Compose, kind, kubectl, kustomize, GitHub Actions, GHCR.

Out of scope unless a concrete need arises: Redis, Kafka, microservices, cloud
infrastructure, authentication, Helm, a Prometheus/Grafana deployment, GitOps controllers.
See `docs/narrative.md` → *Optional later beats* for topics deliberately deferred.

## Running locally

```
uv sync
uv run uvicorn beacon.api.app:app --reload      # API on :8000, checker runs in-process
uv run pytest                                    # test suite
uv run ruff check && uv run ruff format --check  # lint + format (the CI `test` check)
```

Configuration is read from `BEACON_`-prefixed environment variables (see `beacon/config.py`).

## Status

Beat 1.1 in progress: minimal FastAPI service — `Monitor` CRUD, in-process checker,
in-memory storage behind the `Storage` seam, `/health/*` stubs, JSON logging, pytest suite,
and the CI `test` workflow. Not yet containerised or deployed.

## Repository layout (planned)

```
beacon/               application package
  api/                the FastAPI service
  checker/            the checker worker
  storage/            Storage protocol + in-memory and Postgres implementations
  models.py           shared domain models
tests/                pytest suite
migrations/           Alembic migrations
pyproject.toml
Dockerfile
docker-compose.yml    local dev database
Makefile              cluster provisioning + bootstrap
kind/                 per-environment kind cluster configs
k8s/
  base/               shared Kubernetes manifests
  overlays/           dev / staging / prod kustomize overlays
.github/workflows/    CI/CD pipelines
docs/
  narrative.md        the beat-by-beat script
  adr/                architecture decision records
CONTEXT.md            domain glossary
```
