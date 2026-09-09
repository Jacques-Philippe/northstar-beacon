# Beacon — Narrative Script

The planned story arc for the Beacon simulation. This is the **director's script**: it is
allowed to be known to the learner. Knowing the arc does not spoil the exercise — the
moment-to-moment work (writing code, reading logs, forming a diagnosis before the answer is
given) is where the learning happens. Individual failures are still revealed gradually
within a beat.

Keep this document in sync as beats are played, amended, or reordered. Record *what
actually happened* (including divergences from the script) in `docs/log.md`.

## Design principle: into the cluster fast

The goal of the project is Kubernetes and deployment-lifecycle fluency, so the learner is
deploying to a local **kind** cluster by **Beat 1.3** — with a deliberately trivial app.
From that point on, *every* change ships the same way:

> edit code → build image with an immutable tag → load into kind → update the manifest →
> `kubectl rollout` → observe

New capabilities (history, Postgres, config, probes, splitting the checker, StatefulSets,
CI/CD) are then layered on top of an app that is *already running in the cluster*. The
deployment loop is the spine of the course, not a chapter in the middle.

**Environments arrive in two stages.** Acts 1–3 run entirely against a single `beacon-dev`
kind cluster. The `beacon-staging` and `beacon-prod` clusters, the kustomize overlay
restructure, and the promotion pipeline all land together in Act 4 — so multi-environment
work is a deliberate CI/CD lesson, not upfront ceremony. See ADR-0004 and ADR-0005.

## Process

The project runs on a public GitHub repository. Each beat's **Trigger** is turned into a
**GitHub issue** before its **Build** starts, and the work lands as a **pull request** that
closes that issue. The CI/CD pipeline (Act 4) is a committed deliverable, not optional.
Settled design decisions are recorded in `docs/adr/`; domain vocabulary in `CONTEXT.md`.
See `CLAUDE.md`.

## Cast

| Name | Role | Function in the story |
|------|------|-----------------------|
| **(the learner)** | Developer | Real person. Does the work. |
| **Michael** | Product Owner | Requirements, priorities, scope changes, changes of mind. |
| **Andy** | Infrastructure engineer | Cluster, containers, CI/CD, pushes back on infra debt. |
| **Stanley** | Engineering manager | Prioritisation calls, sign-off, escalations. |
| **Various** | Other devs / users | Bug reports, complaints from monitored teams. |

## Conventions

- **Trigger** — the stakeholder message or event that opens the beat.
- **Build** — what the learner is expected to implement.
- **Complication** — the realistic problem introduced. Not revealed all at once; the learner
  investigates.
- **Lesson** — the intended takeaway.
- **Roadmap ref** — corresponding step(s) in `README.md`'s roadmap.

Failures are deliberately varied in root cause: application bug, Kubernetes/config error,
database/dependency failure, or the monitored target genuinely being down.

---

## Act 1 — Into the cluster

*(single `beacon-dev` cluster throughout)*

### Beat 1.1 — A minimal service

- **Trigger.** Michael: "I want to see which services we're monitoring and whether they're
  up right now." He wants a list of monitored endpoints plus their latest check result.
- **Build.** `Monitor` CRUD; an in-process checker loop that probes each monitor on its
  interval; current status derived from the latest check. Storage behind a narrow `Storage`
  protocol with an `InMemoryStorage` implementation (ADR-0008). `/health/live` and
  `/health/ready` stubs (both return 200 for now). Structured JSON logging from the start.
  pytest suite.
- **Complication.** None — this beat establishes the baseline. Keep it small.
- **Lesson.** Shape of the app; what liveness vs. readiness will come to mean; why the
  storage seam exists.
- **Roadmap ref.** 1.

### Beat 1.2 — Containerise

- **Trigger.** Andy: "If you want this anywhere near the cluster it needs to be an image."
- **Build.** `Dockerfile` (Python 3.12, `uv` for dependency install from `pyproject.toml`),
  `.dockerignore`; a tag scheme based on the git short SHA (no `latest`). One image, two
  entrypoints — the container command selects `api` or `checker`. Build and run locally;
  confirm the API answers on the published port.
- **Complication.** One realistic Docker gotcha: wrong port exposed, a dev-only dependency
  missing from the image, or the app binding to `127.0.0.1` instead of `0.0.0.0`.
- **Lesson.** Source vs. build artifact vs. image vs. container. Build context. Why the
  container environment differs from the laptop.
- **Roadmap ref.** 2.

### Beat 1.3 — Deploy to kind

- **Trigger.** Andy: "Cluster's ready. Get Beacon running on it."
- **Build.** Provision the `beacon-dev` kind cluster from a committed `Makefile` +
  `kind/dev.yaml` (`make dev-up`). Load the image; a `Deployment` (1 replica) and a
  `Service` for `api`; reach the API via `kubectl port-forward`. Walk the
  `kubectl get / describe / logs` loop. The checker still runs in-process inside `api`.
- **Complication.** The first deploy does not work: `ImagePullBackOff` because the image was
  never loaded into kind, or a `containerPort` / Service `targetPort` mismatch so
  port-forward connects to nothing.
- **Lesson.** Desired state → controllers → actual state. Pod / ReplicaSet / Deployment /
  Service and how they relate. How an image gets to a node in kind.
- **Roadmap ref.** 3.

### Beat 1.4 — The deploy loop becomes routine

- **Trigger.** Michael: "Small thing — can each monitor record which team owns it?"
- **Build.** Add `owning_team` to `Monitor`. Ship it: rebuild the image with a new SHA tag,
  update the manifest's image reference, `kubectl apply`, watch `kubectl rollout status`.
- **Complication.** If the learner reuses a tag or edits in place: the rollout does nothing
  visible / Pods don't restart. Surfaces why immutable tags matter.
- **Lesson.** The full loop, internalised. Why `latest` breaks both rollout and rollback.
  A rollout is a controlled ReplicaSet swap.
- **Roadmap ref.** 4.

---

## Act 2 — State forces the architecture

*(single `beacon-dev` cluster throughout)*

### Beat 2.1 — History creeps in

- **Trigger.** Michael: "Can we get an uptime % for the last day and the last week, and a
  list of past incidents?"
- **Build.** `CheckResult` (append-only), `Incident` (opens after N consecutive failures,
  closes on recovery), `/monitors/{id}/uptime`, `/incidents`, `/status`. Ship through the
  loop.
- **Complication.** None yet — the trap is set in 2.2.
- **Lesson.** Deriving uptime from incidents rather than scanning every result.
- **Roadmap ref.** 5.

### Beat 2.2 — Pods are ephemeral

- **Trigger.** After the next rollout (or a `kubectl delete pod`), Michael: "Why is all our
  uptime history back to 100%? We had an incident logged this morning."
- **Build.** Nothing new to build — this beat is investigation and a decision. The learner
  should conclude that in-memory state cannot live in a Pod.
- **Complication.** Every rollout and every rescheduled Pod wipes all history.
- **Lesson.** Pods are disposable by design; application instances are cattle. State that
  must survive a Pod cannot live inside one. This is the forcing function for a database.
- **Roadmap ref.** 6.

### Beat 2.3 — PostgreSQL

- **Trigger.** Following 2.2: give Beacon somewhere durable to write.
- **Build.** Add a `PostgresStorage` implementation of the `Storage` protocol — SQLAlchemy
  2.0 ORM, synchronous, typed models (ADR-0009). Docker Compose runs Postgres for the local
  dev inner loop. In the cluster, Postgres runs as a `Deployment` with an `emptyDir` volume
  for now (**deliberately naive** — still not durable; this is the setup for Act 3). The app
  reads its connection URL from the environment.
- **Complication.** "Works in Compose, fails in kind": the DB host is still `localhost`
  instead of the Postgres `Service` name; or the app starts before Postgres accepts
  connections and crashes once.
- **Lesson.** Cluster DNS and Service names. The app now has a dependency it doesn't
  control the lifecycle of. Swapping a `Storage` implementation without touching call sites.
- **Roadmap ref.** 7.

### Beat 2.4 — Config out of the image

- **Trigger.** Andy: "The DB connection details are baked into the image. That's not going
  to fly once there's more than one environment."
- **Build.** `ConfigMap` for non-secret config (DB host, port, name, check defaults, log
  level); `Secret` for the DB username/password, created out-of-band by a bootstrap script
  and never committed (sealed-secrets is an *Optional later beat*). Wire both into
  the Pod via env. Manifests stay flat for now — the kustomize base/overlay restructure
  comes with the second environment in Beat 4.2.
- **Complication.** A wrong value in the ConfigMap (DB host typo) → `CrashLoopBackOff`.
  Diagnose from `kubectl describe`, logs, and the restart count / backoff.
- **Lesson.** Config is separate from the image and separately deployable. A bad config
  presents identically to a bad app until you read the error.
- **Roadmap ref.** 8.

### Beat 2.5 — Migrations

- **Trigger.** A schema change is needed — e.g. an index on `check_result (monitor_id,
  checked_at)` because `/uptime` has gotten slow, or a new nullable column.
- **Build.** Wire up Alembic (ADR-0009); a baseline migration for the existing schema; the
  change as a second migration. Run migrations as a Kubernetes `Job` (or init container)
  ordered before the new Pods roll.
- **Complication.** A migration that succeeds against an empty dev database behaves badly
  against realistic data: adds a `NOT NULL` column with no default, or takes a lock that
  blocks writes.
- **Lesson.** Migrations are code that runs against real data. Forward/backward
  compatibility during a rolling update (old and new code briefly coexist). Ordering of
  "migrate" vs. "new pods".
- **Roadmap ref.** 9.

---

## Act 3 — Running it properly

*(single `beacon-dev` cluster throughout)*

### Beat 3.1 — Readiness vs. liveness

- **Trigger.** During a rollout, a Pod takes traffic before it can serve it and users get
  errors for ~10 seconds.
- **Build.** Real probes: `/health/ready` checks the DB connection; `/health/live` stays a
  cheap liveness signal. Configure `readinessProbe` and `livenessProbe` on both workloads.
- **Complication (staged).**
  1. Pod `Running` but never `Ready` — readiness checks the DB, DB is briefly unreachable
     on startup, readiness flaps.
  2. A liveness probe with too short a `timeoutSeconds` under load → container killed and
     restarted in a loop.
- **Lesson.** Readiness gates traffic; liveness gates restarts; they are not
  interchangeable. Kubernetes does **not** roll back a Deployment just because the new Pods
  never become Ready — the old ReplicaSet stays up and the rollout simply stalls.
- **Roadmap ref.** 10.

### Beat 3.2 — Resource requests and limits

- **Trigger.** Andy: "Your Pods have no requests or limits. On a shared cluster that's how
  you get evicted at 3am."
- **Build.** Set `requests` and `limits` for CPU and memory on `api`, `checker`, and
  Postgres.
- **Complication.** A memory `limit` set too low → `OOMKilled`, visible in
  `kubectl describe` as the last state. Or `requests` set so high the Pod stays `Pending`
  with `FailedScheduling`.
- **Lesson.** Requests drive scheduling; limits are enforced hard. What "the scheduler
  couldn't place this Pod" looks like.
- **Roadmap ref.** 11.

### Beat 3.3 — Scale the API, split the checker

- **Trigger.** Stanley: "Beacon itself can't be a single point of failure. Run more than
  one."
- **Build.** Scale `api` to 3 replicas. Observe that each replica runs its own in-process
  checker → every target is now probed 3×. Split the checker into its **own Deployment**
  (1 replica) and remove the loop from `api`.
- **Complication.** A monitored team messages: "Beacon is hitting our health endpoint every
  10 seconds, we configured 30."
- **Lesson.** Stateless replicas behind a Service are easy. A background worker is not
  stateless-by-nature — running N copies changes behaviour. Separating workloads that scale
  differently.
- **Roadmap ref.** 12.

### Beat 3.4 — Should Postgres even be in the cluster?

- **Trigger.** Stanley: "Before we make the database a permanent fixture in here — do we
  actually want to be running our own Postgres?"
- **Build.** A decision record, `docs/adr/0010-postgres-in-cluster.md`: the full
  managed-vs-in-cluster analysis (backups, failover, upgrades, on-call expertise, cost,
  blast radius), landing on **in-cluster** — referencing ADR-0003, since a managed database
  costs money and the project has a zero-spend constraint. The record must state plainly
  that a real shop would use a managed service.
- **Complication.** None — this is a judgement beat. The *outcome* is constrained; the
  *reasoning* is the exercise, and it is exactly the kind of tradeoff an interviewer probes.
- **Lesson.** Not every workload belongs in Kubernetes. Recognising when a constraint (not
  an engineering preference) is driving an architecture decision.
- **Roadmap ref.** 13.

### Beat 3.5 — StatefulSet and PVC

- **Trigger.** Following 3.4: replace the throwaway `emptyDir` Postgres with something
  durable.
- **Build.** Postgres as a `StatefulSet` with a `volumeClaimTemplate`; a headless Service.
  Verify data now survives a Pod delete.
- **Complication.** Data survives `kubectl delete pod` but not `kubectl delete pvc`;
  scaling the StatefulSet down leaves the PVC behind; the Pod comes back with a stable name
  and re-attaches its volume.
- **Lesson.** Pod lifecycle and storage lifecycle are separate, and storage is
  deliberately sticky. What a StatefulSet gives you (stable identity, ordered rollout,
  per-Pod storage) and what it does **not** (replication, failover, backups).
- **Roadmap ref.** 14.

### Beat 3.6 — Multiple checker replicas

- **Trigger.** The single checker can't keep up with the number of monitors; checks are
  falling behind their intervals.
- **Build.** Scale `checker` to N replicas; add a claim query
  (`SELECT ... FOR UPDATE SKIP LOCKED`) so each due check is taken by exactly one replica.
- **Complication.** Before the claim query: double-probing returns, now from multiple
  checker Pods; a monitored team complains again.
- **Lesson.** Horizontally scaling a worker needs an explicit coordination mechanism.
  DB-level locking vs. leader election vs. a real queue — the tradeoffs, and why "just add
  replicas" is safe for `api` but not for `checker`.
- **Roadmap ref.** 15.

### Beat 3.7 — A metrics endpoint

- **Trigger.** Andy: "When the checker fell behind, how would we have known before the
  monitored teams told us?"
- **Build.** A Prometheus `/metrics` endpoint on `api` (and the checker): check throughput,
  probe latency, queue depth / lag, incident counts. **No** Prometheus or Grafana
  deployment — the endpoint and a documented `kubectl port-forward` + `curl` is enough for
  the exercise.
- **Complication.** None required; optionally, a metric that lies (a counter reset on every
  scrape because it's per-request state).
- **Lesson.** Instrumentation as a first-class concern; the difference between logs (events)
  and metrics (aggregates); why you don't need the whole observability stack to get value.
- **Roadmap ref.** 16.

---

## Act 4 — CI/CD, multiple environments, and the failure gauntlet

### Beat 4.1 — The pipeline

- **Trigger.** Andy: "You've been deploying by hand for weeks. Let's automate it before
  someone fat-fingers a tag."
- **Build.** GitHub Actions: run the pytest suite on every PR as the `test` check (already
  required by `protect-master`). On merge to `master`: build the image, tag it with the git
  short SHA, push to GHCR, and auto-deploy to **`beacon-dev`**.
- **Complication.** A pipeline that pushes `:latest` and a Deployment whose image reference
  never changes → "CI is green, why didn't my change deploy?"
- **Lesson.** The pipeline as: source → build artifact → image → registry → Deployment
  update → rollout → Pods. Immutable tags are what make that chain auditable and
  reversible.
- **Roadmap ref.** 17.

### Beat 4.2 — Staging and production

- **Trigger.** Stanley: "dev is not where we demo. Stand up staging and prod, and make
  releasing to them boring."
- **Build.**
  - Provision `beacon-staging` and `beacon-prod` kind clusters (`make staging-up`,
    `make prod-up`; `kind/staging.yaml`, `kind/prod.yaml`).
  - Restructure manifests into kustomize `base/` + `overlays/{dev,staging,prod}/` (ADR-0006).
    Overlays vary replica count, resource requests/limits, log level, image tag, and per-env
    Secret/ConfigMap values. Each environment gets its own isolated Postgres (ADR-0005).
  - Promotion (ADR-0007): merge → dev automatically; a gated `workflow_dispatch` (GitHub
    Environments, self-review) re-points the **staging** then **prod** overlay at the
    already-built, already-tested SHA tag — no rebuild. Each promotion is a commit bumping
    the overlay tag.
  - Seed each environment's `Monitor` rows separately (dev watches throwaway targets, prod
    watches "real" Northstar services) — target lists are DB data, not overlay config.
- **Complication.** "Works in dev, not in staging": an overlay patch typo, a Secret that was
  only ever created in the dev cluster, or a `kubectl` context left pointing at the wrong
  cluster.
- **Lesson.** Build once, promote the artifact. `kubectl` contexts and the danger of the
  ambient one. What legitimately differs between environments vs. what must be identical.
- **Roadmap ref.** 18.

### Beat 4.3 — Ship, then roll back

- **Trigger.** Michael: "Send a webhook when an incident opens." (v1.1 — a real feature.)
- **Build.** The webhook feature, shipped through the pipeline: merge → dev, promote →
  staging → prod.
- **Complication.** v1.2 promotes a bad config value to prod → rolling update, some Pods
  come up broken, `/status` fails for a fraction of traffic → roll back by re-pointing the
  prod overlay at the previous tag.
- **Lesson.** Rolling update mechanics (`maxSurge` / `maxUnavailable`); partial failure
  mid-rollout; Kubernetes does not auto-roll-back; rollback is promoting a known-good
  artifact, not a rebuild; what state the database is left in.
- **Roadmap ref.** 19.

### Beat 4.4 — The gauntlet

Each sub-beat is an independent incident, shipped to prod through the pipeline. The learner
forms a diagnosis *before* the cause is confirmed. Root causes are deliberately spread
across categories.

| Version | Symptom | Root cause | Correct diagnosis |
|---------|---------|-----------|-------------------|
| **v2.0** | HTTP 500s on `/status` | Incident-close logic throws on a null `resolved_at` | The application is broken. Not Kubernetes. |
| **v2.1** | Pods flap Ready/NotReady, traffic drops | `/health/ready` changed to also check a flaky external dependency | The readiness probe / config is wrong. The app is fine. |
| **v2.2** | `api` returns 503, `checker` in `CrashLoopBackOff` | Postgres PVC full / Pod evicted | A dependency is down. Beacon is behaving correctly. |
| **v2.3** | Behaviour differs between Pods for the "same" version | A stale ReplicaSet still serving / a node with an old cached image | Not every Pod is running what you think it is. |

- **Roadmap ref.** 20.

---

## Cross-cutting stakeholder churn

Dropped into the acts where they bite hardest, not run as a separate phase.

| Churn | Where it lands | Point |
|-------|----------------|-------|
| Michael redefines what "degraded" means after it's built | After 2.1, or during Act 3 | Requirements change post-implementation; estimate and communicate the cost. |
| Priority flip: an urgent feature mid-Act-3; Andy pushes back on the infra debt it displaces | Mid Act 3 | Competing priorities; making the tradeoff explicit to stakeholders. |
| Michael asks for a "simple" feature that turns out to have deployment implications | Act 3 or 4 | A change can be small in code and large in operations. |

---

## Optional later beats

Introduce only if the story wants them; each is a real topic deferred to keep the spine
clear.

- **Sealed Secrets / SOPS / External Secrets** — encrypted secrets committed to the repo,
  replacing the out-of-band bootstrap script.
- **GitOps (Argo CD / Flux)** — a controller in each cluster reconciling from the repo,
  replacing the push-style promotion of Beat 4.2.
- **Package Beacon as a Helm chart** — if a distribution / templating angle becomes
  interesting.
- **Staging as a namespace** instead of its own cluster — the fallback if three kind
  clusters strains the laptop (ADR-0005).
- **Async SQLAlchemy** — if request throughput ever makes the sync-in-threadpool model the
  bottleneck (ADR-0009).

## Open questions / to decide

- How migrations are triggered in the pipeline (Job before rollout vs. init container) —
  settle when Beat 2.5 is played.
