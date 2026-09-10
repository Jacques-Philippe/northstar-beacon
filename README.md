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
| **Monitor** | An HTTP endpoint Beacon watches. | `id`, `name`, `url`, `method`, `expected_status`, `interval_seconds`, `timeout_seconds`, `enabled`, `owning_team`, `created_at` |
| **CheckResult** | The outcome of one probe. Append-only, high-volume. | `id`, `monitor_id`, `checked_at`, `ok`, `status_code`, `response_ms`, `error` |
| **Incident** | Opens once a run of consecutive failing checks reaches `BEACON_INCIDENT_FAILURE_THRESHOLD` (default 3), backdated to the first failure in that run; closes on the first success. | `id`, `monitor_id`, `opened_at`, `resolved_at` |

Derived state:

- **Current status** of a monitor — from its latest `CheckResult` (`up` / `down`;
  `unknown` before the first probe). `degraded` is a later beat.
- **Uptime %** for the last day and the last week — one minus the share of the window
  covered by incidents, clipped to the window edges. Computed from incidents, never by
  scanning `CheckResult`s.

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
| GET    | `/monitors/{id}/results` | Recent check results (`?since=`) — *later beat* |
| GET    | `/monitors/{id}/uptime` | Uptime % for the last day and the last week |
| GET    | `/incidents` | Incident history (`?monitor_id=`) |
| GET    | `/status` | Dashboard summary across all monitors |
| GET    | `/health/live` | Liveness — is the process up? |
| GET    | `/health/ready` | Readiness — can it serve traffic (e.g. DB reachable)? |

## Components

Beacon is three logical components:

- **api** — the FastAPI service above.
- **checker** — a loop that finds monitors whose next check is due, probes them, writes
  `CheckResult`s, and opens/closes `Incident`s.
- **frontend** — a Vue single-page app that renders the status page, uptime numbers, and
  incident history, read-only. Its own image (multi-stage build, served by nginx); reaches
  `api` through an Ingress. Introduced in Act 2, not Act 1 (ADR-0011).

The api and checker start fused: the checker runs as a background task **inside the api
process**, on
in-memory data — that is what gets containerised and deployed to kind first. How and when
they come apart — the checker into its own Deployment, then multiple checker replicas with a
real stateful-coordination problem (`SELECT … FOR UPDATE SKIP LOCKED` / leader election) —
is driven by specific beats in `docs/narrative.md`, not decided up front.

## Target architecture (built up gradually, not all at once)

- Python 3.12 / FastAPI application, plus the checker worker; `uv` + `pyproject.toml`
- A Vue 3 / Vite single-page frontend, built into its own nginx image (multi-stage build)
- One container image, two entrypoints (`api` / `checker`); immutable git-SHA tags
- PostgreSQL for persistent data, via a `Storage` interface (SQLAlchemy 2.0 ORM + Alembic)
- Docker Compose for the local dev database
- Kubernetes for orchestration: three local **kind** clusters (`dev` / `staging` / `prod`)
- Kubernetes objects introduced as they become relevant:
  Deployments, Services, Ingress (+ an ingress-nginx controller), ConfigMaps, Secrets,
  readiness/liveness probes, resource requests/limits, PVCs, StatefulSets, Jobs
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
- **Act 2 — State forces the architecture.** Add history → a Vue frontend behind an Ingress
  → feel Pod ephemerality → introduce PostgreSQL → move config out of the image → database
  migrations.
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

Python 3.12, `uv`, FastAPI, pytest, SQLAlchemy 2.0 + Alembic, PostgreSQL, Vue 3, Vite,
vitest, nginx, Docker, Docker Compose, kind, kubectl, kustomize, ingress-nginx, GitHub
Actions, GHCR.

Out of scope unless a concrete need arises: Redis, Kafka, microservices, cloud
infrastructure, authentication, Helm, a Prometheus/Grafana deployment, GitOps controllers.
See `docs/narrative.md` → *Optional later beats* for topics deliberately deferred.

## Running locally

```
uv sync
uv run python -m beacon api                       # API on :8000, checker runs in-process
uv run python -m beacon checker                   # the probe loop on its own
uv run pytest                                     # test suite
uv run ruff check && uv run ruff format --check   # lint + format (the CI `test` check)
```

`python -m beacon <api|checker>` is the single entrypoint; the argument selects the
process, and it is the same dispatch the container image uses.

Configuration is read from `BEACON_`-prefixed environment variables (see `beacon/config.py`).

## Container image

One image, two entrypoints. Tags are the immutable git short SHA — never `latest`.

```
make image                                        # docker build -t beacon:<short-sha> .
make run-api                                       # build, then run `api` on localhost:8000
make run-checker                                    # build, then run `checker`

docker run --rm -p 8000:8000 beacon:<short-sha> api
docker run --rm beacon:<short-sha> checker
```

The build is multi-stage: `uv` resolves the virtualenv in the build stage; the runtime
stage carries only Python and the venv, and runs as a non-root user.

## Deploying to kind (dev)

Beat 1.3: the image runs on a local **kind** cluster, `beacon-dev`. One `Deployment`
(1 replica, checker still in-process) and a `ClusterIP` `Service`; the API is reached with
`kubectl port-forward` (an Ingress replaces that in Beat 2.3). Manifests are kustomize:
`k8s/base/` + `k8s/overlays/dev/`, the overlay pinning the immutable git-SHA image tag.

### Prerequisites

| Tool | Why | Install (macOS) |
|------|-----|-----------------|
| **Docker** | kind runs the cluster as a container; the image is built here | Docker Desktop — must be **running** before `make dev-up` |
| **kind** | provisions the local Kubernetes cluster | `brew install kind` |
| **kubectl** | talks to the cluster; also provides the kustomize build (`apply -k`) | `brew install kubectl` |

No standalone `kustomize` binary is needed — `kubectl` has it built in. Verify the setup:

```
docker info >/dev/null && kind version && kubectl version --client
```

### Make targets

| Command | What it does |
|---------|--------------|
| `make dev-up` | Create the `beacon-dev` kind cluster from `kind/dev.yaml`. Sets the `kind-beacon-dev` kubectl context. |
| `make dev-down` | Delete the `beacon-dev` cluster. |
| `make image` | `docker build` the image, tagged `beacon:<git short SHA>`. |
| `make kind-load` | Build (via `make image`) and side-load the image into the kind node — kind has no registry access, so nothing is *pulled*. |
| `make deploy-dev` | Full deploy loop: `kind-load`, rewrite `k8s/overlays/dev` to the current SHA, `kubectl apply -k`, then wait on `kubectl rollout status`. |
| `make dev-status` | `kubectl get deploy,rs,pod,svc -l app=beacon` — the get/describe/logs loop starts here. |

### First deploy

```
make dev-up
make deploy-dev

# reach the API (Service listens on 80, forwards to the container's 8000)
kubectl --context kind-beacon-dev port-forward svc/beacon-api 8000:80
curl localhost:8000/health/live        # {"status":"ok"}

make dev-down                          # when you're done
```

Override the image name with `make image IMAGE=beacon-local`; the SHA tag is always the
current `git rev-parse --short HEAD`.

## Status

Beat 1.4 in progress: the deploy loop is now routine. `owning_team` was added to `Monitor`
(create / read / patch) and shipped through rebuild → new SHA tag → overlay bump →
`kubectl apply` → `kubectl rollout status`. Persistence is still in-memory (Act 2), so no
storage or migration work.

Beat 1.3: the containerised service deploys to the `beacon-dev` kind cluster —
`kind/dev.yaml`, kustomize manifests under `k8s/`, and `Makefile` targets for provisioning,
image side-load, and rollout. Reached via `kubectl port-forward`.

## Repository layout (planned)

```
beacon/               application package
  api/                the FastAPI service
  checker/            the checker worker
  storage/            Storage protocol + in-memory and Postgres implementations
  models.py           shared domain models
frontend/             Vue 3 / Vite single-page app (own image, nginx-served)
tests/                pytest suite
migrations/           Alembic migrations
pyproject.toml
Dockerfile            api / checker image
frontend/Dockerfile   multi-stage frontend image (node build -> nginx)
docker-compose.yml    local dev database
Makefile              image build + run; later, cluster provisioning + bootstrap
kind/                 per-environment kind cluster configs
k8s/
  base/               shared Kubernetes manifests (api, checker, frontend, ingress)
  overlays/           dev / staging / prod kustomize overlays
.github/workflows/    CI/CD pipelines
docs/
  narrative.md        the beat-by-beat script
  adr/                architecture decision records
CONTEXT.md            domain glossary
```
