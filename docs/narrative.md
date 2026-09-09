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

## Process

The project runs on a public GitHub repository. Each beat's **Trigger** is turned into a
**GitHub issue** before its **Build** starts, and the work lands as a **pull request** that
closes that issue. The CI/CD pipeline (Act 4) is a committed deliverable, not optional. See
`CLAUDE.md`.

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

### Beat 1.1 — A minimal service

- **Trigger.** Michael: "I want to see which services we're monitoring and whether they're
  up right now." He wants a list of monitored endpoints plus their latest check result.
- **Build.** `Monitor` CRUD; an in-process checker loop that probes each monitor on its
  interval; current status derived from the latest check. In-memory storage.
  `/health/live` and `/health/ready` stubs (both return 200 for now). pytest suite.
- **Complication.** None — this beat establishes the baseline. Keep it small.
- **Lesson.** Shape of the app; what liveness vs. readiness will come to mean.
- **Roadmap ref.** 1.

### Beat 1.2 — Containerise

- **Trigger.** Andy: "If you want this anywhere near the cluster it needs to be an image."
- **Build.** `Dockerfile`, `.dockerignore`; a tag scheme based on the git short SHA (no
  `latest`); build and run the container locally; confirm the API answers on the published
  port.
- **Complication.** One realistic Docker gotcha: wrong port exposed, a dev-only dependency
  missing from the image, or the app binding to `127.0.0.1` instead of `0.0.0.0`.
- **Lesson.** Source vs. build artifact vs. image vs. container. Build context. Why the
  container environment differs from the laptop.
- **Roadmap ref.** 2.

### Beat 1.3 — Deploy to kind

- **Trigger.** Andy: "Cluster's ready. Get Beacon running on it."
- **Build.** Create the kind cluster; load the image; a `Deployment` (1 replica) and a
  `Service`; reach the API via `kubectl port-forward`. Walk the
  `kubectl get / describe / logs` loop.
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
- **Build.** Add PostgreSQL. Docker Compose runs Postgres for the local dev inner loop. In
  the cluster, Postgres runs as a `Deployment` with an `emptyDir` volume for now
  (**deliberately naive** — still not durable; this is the setup for Act 3). App talks to
  the DB via a connection URL from the environment.
- **Complication.** "Works in Compose, fails in kind": the DB host is still `localhost`
  instead of the Postgres `Service` name; or the app starts before Postgres accepts
  connections and crashes once.
- **Lesson.** Cluster DNS and Service names. The app now has a dependency it doesn't
  control the lifecycle of.
- **Roadmap ref.** 7.

### Beat 2.4 — Config out of the image

- **Trigger.** Andy: "The DB connection details are baked into the image. That's not going
  to fly for more than one environment."
- **Build.** `ConfigMap` for non-secret config (DB host, port, name, check defaults);
  `Secret` for the DB username/password; wire both into the Pod via env.
- **Complication.** A wrong value in the ConfigMap (DB host typo) → `CrashLoopBackOff`.
  Diagnose from `kubectl describe`, logs, and the restart count / backoff.
- **Lesson.** Config is separate from the image and separately deployable. A bad config
  presents identically to a bad app until you read the error.
- **Roadmap ref.** 8.

### Beat 2.5 — Migrations

- **Trigger.** A schema change is needed — e.g. an index on `check_result (monitor_id,
  checked_at)` because `/uptime` has gotten slow, or a new nullable column.
- **Build.** Introduce Alembic; a baseline migration for the existing schema; the change as
  a second migration. Decide how migrations run relative to a rollout (init container / Job
  / manual step).
- **Complication.** A migration that succeeds against an empty dev database behaves badly
  against realistic data: adds a `NOT NULL` column with no default, or takes a lock that
  blocks writes.
- **Lesson.** Migrations are code that runs against production data. Forward/backward
  compatibility during a rolling update (old and new code briefly coexist). Ordering of
  "migrate" vs. "new pods".
- **Roadmap ref.** 9.

---

## Act 3 — Running it properly

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
- **Build.** A short written decision record (`docs/decisions/0001-postgres-hosting.md`):
  managed vs. in-cluster, weighing backups, failover, upgrades, on-call expertise, cost,
  and blast radius.
- **Complication.** None — this is a judgement beat.
- **Lesson.** Not every workload belongs in Kubernetes. Decision **for the exercise**: run
  in-cluster with real persistent storage in order to learn the primitives, with an
  explicit note that production would use a managed service.
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

---

## Act 4 — CI/CD and the failure gauntlet

### Beat 4.1 — The pipeline

- **Trigger.** Andy: "You've been deploying by hand for weeks. Let's automate it before
  someone fat-fingers a tag."
- **Build.** GitHub Actions: run tests → build the image → push to GHCR with an immutable
  tag (git SHA) → update the manifest → `kubectl rollout` → verify readiness.
- **Complication.** A pipeline that pushes `:latest` and a Deployment whose image reference
  never changes → "CI is green, why didn't my change deploy?"
- **Lesson.** The pipeline as: source → build artifact → image → registry → Deployment
  update → rollout → Pods. Immutable tags are what make that chain auditable and
  reversible.
- **Roadmap ref.** 16.

### Beat 4.2 — Ship, then roll back

- **Trigger.** Michael: "Send a webhook when an incident opens." (v1.1 — a real feature.)
- **Build.** The webhook feature, shipped through the pipeline as a rolling update.
- **Complication.** v1.2 ships a bad config value → rolling update, some Pods come up
  broken, `/status` fails for a fraction of traffic → `kubectl rollout undo`.
- **Lesson.** Rolling update mechanics (`maxSurge` / `maxUnavailable`); partial failure
  mid-rollout; Kubernetes does not auto-roll-back; how to roll back deliberately and what
  state the database is left in.
- **Roadmap ref.** 17.

### Beat 4.3 — The gauntlet

Each sub-beat is an independent incident. The learner forms a diagnosis *before* the cause
is confirmed. Root causes are deliberately spread across categories.

| Version | Symptom | Root cause | Correct diagnosis |
|---------|---------|-----------|-------------------|
| **v2.0** | HTTP 500s on `/status` | Incident-close logic throws on a null `resolved_at` | The application is broken. Not Kubernetes. |
| **v2.1** | Pods flap Ready/NotReady, traffic drops | `/health/ready` changed to also check a flaky external dependency | The readiness probe / config is wrong. The app is fine. |
| **v2.2** | `api` returns 503, `checker` in `CrashLoopBackOff` | Postgres PVC full / Pod evicted | A dependency is down. Beacon is behaving correctly. |
| **v2.3** | Behaviour differs between Pods for the "same" version | A stale ReplicaSet still serving / a node with an old cached image | Not every Pod is running what you think it is. |

- **Roadmap ref.** 18.

---

## Cross-cutting stakeholder churn

Dropped into the acts where they bite hardest, not run as a separate phase.

| Churn | Where it lands | Point |
|-------|----------------|-------|
| Michael redefines what "degraded" means after it's built | After 2.1, or during Act 3 | Requirements change post-implementation; estimate and communicate the cost. |
| Priority flip: an urgent feature mid-Act-3; Andy pushes back on the infra debt it displaces | Mid Act 3 | Competing priorities; making the tradeoff explicit to stakeholders. |
| Michael asks for a "simple" feature that turns out to have deployment implications | Act 3 or 4 | A change can be small in code and large in operations. |

---

## Open questions / to decide

- Migrations tool: Alembic assumed. Confirm.
- Do we ever introduce a second environment (staging), or stay single-environment?
- How far to take observability (structured logging only, or a metrics endpoint too)?
