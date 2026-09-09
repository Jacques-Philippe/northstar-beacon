# Beacon — Narrative Script

The planned story arc for the Beacon simulation. This is the **director's script**: it is
allowed to be known to the learner. Knowing the arc does not spoil the exercise — the
moment-to-moment work (writing code, reading logs, forming a diagnosis before the answer is
given) is where the learning happens. Individual failures are still revealed gradually
within a beat.

Keep this document in sync as beats are played, amended, or reordered. Record *what
actually happened* (including divergences from the script) in `docs/log.md`.

## Cast

| Name | Role | Function in the story |
|------|------|-----------------------|
| **(the learner)** | Developer | Real person. Does the work. |
| **Marta** | Product Owner | Requirements, priorities, scope changes, ambiguity, changes of mind. |
| **Priya** | Infrastructure engineer | Containerisation, cluster, CI/CD, pushes back on infra debt. |
| **Dan** | Engineering manager | Prioritisation calls, sign-off, escalations. |
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

## Act 1 — A simple service (in-memory)

### Beat 1.1 — The first ask

- **Trigger.** Marta: "I want to see which services we're monitoring and whether they're up."
- **Ambiguity.** "Up" — right now, or historically? Learner should clarify before building.
  Marta means: a list of monitored endpoints plus their latest check result.
- **Build.** `Monitor` CRUD; an in-process checker loop; current status derived from the
  latest check. In-memory storage. pytest suite.
- **Complication.** None yet — this beat establishes the baseline.
- **Lesson.** Shape of the app; readiness vs. liveness as concepts (`/health/*` stubs).
- **Roadmap ref.** 1.

### Beat 1.2 — History creeps in

- **Trigger.** Marta: "Can we get an uptime % for the last day and the last week?"
- **Build.** `CheckResult` (append-only), `Incident` (open after N consecutive failures,
  close on recovery), `/monitors/{id}/uptime`, `/incidents`, `/status`.
- **Complication.** A routine process restart wipes all history; Marta notices the uptime
  numbers reset to 100% and is unhappy. Separately, the in-memory results list grows
  without bound.
- **Lesson.** Two independent pressures toward persistence (durability, and unbounded
  growth). Motivates — but does not yet introduce — a database.
- **Roadmap ref.** 2.

---

## Act 2 — Containers and the database

### Beat 2.1 — Containerise

- **Trigger.** Priya: "Get it into a container so we can run it properly."
- **Build.** Dockerfile; `.dockerignore`; documented build/run.
- **Complication.** One realistic Docker gotcha (pick one when played): wrong port exposed;
  a dev-only dependency that isn't in the image; the checker cannot resolve monitored
  targets from inside the container network.
- **Lesson.** Image vs. container; build context; why the runtime environment differs from
  the laptop.
- **Roadmap ref.** 3.

### Beat 2.2 — Availability pressure splits the app

- **Trigger.** Marta / Dan: "The monitor itself can't be the thing that's down." Push for
  redundancy.
- **Build.** Run 2+ `api` replicas (Compose first). Observe that each replica runs its own
  checker → targets probed N× the configured rate. Split the checker into its own process.
- **Complication.** The two processes now have no shared state — separate in-memory stores
  disagree. This is the forcing function for **PostgreSQL**. Add Compose service for
  Postgres; wire both processes to it.
- **Lesson.** Stateless replicas are easy; shared state is the hard part. The database is
  introduced because the architecture demands it, not by decree.
- **Roadmap ref.** 4.

### Beat 2.3 — Migrations

- **Trigger.** A schema change is needed (e.g. add `owning_team` to `Monitor`, or an index).
- **Build.** Introduce Alembic; baseline migration; the change as a second migration.
- **Complication.** A migration that succeeds on an empty dev database fails against
  realistic data: adds a `NOT NULL` column with no default, or takes a long lock.
- **Lesson.** Migrations are code that runs against production data; forward/backward
  compatibility; the deploy-time ordering of "migrate" vs. "new code".
- **Roadmap ref.** 5.

---

## Act 3 — Kubernetes

### Beat 3.1 — Into kind

- **Trigger.** Priya: "Local cluster is ready — let's get Beacon running on kind."
- **Build.** Deployments for `api` and `checker`; a `Service` for `api`; namespace.
- **Complication.** "Works in Compose, fails in k8s": `ImagePullBackOff` because the image
  was never loaded into kind; or the DB host is still `localhost` instead of the Postgres
  Service name.
- **Lesson.** `kubectl get pods` / `describe` / `logs` as the diagnostic loop; cluster
  networking; how images get to nodes.
- **Roadmap ref.** 6.

### Beat 3.2 — Config and secrets

- **Trigger.** Hardcoded config needs to come out of the image.
- **Build.** `ConfigMap` for non-secret config; `Secret` for DB credentials; wire via env /
  volume.
- **Complication.** A wrong value in the ConfigMap (DB host typo) → `CrashLoopBackOff`.
  Learner diagnoses from `describe` + logs + `kubectl exec`.
- **Lesson.** Config is separate from the image; a bad config looks like a bad app until you
  read the error; restart backoff.
- **Roadmap ref.** 7.

### Beat 3.3 — Probes and limits

- **Trigger.** Pods are being sent traffic before they can serve it; one bad Pod takes
  requests.
- **Build.** Readiness probe (`/health/ready`, checks DB), liveness probe (`/health/live`),
  resource requests/limits.
- **Complication (staged).**
  1. Pod `Running` but not `Ready` — readiness checks the DB, DB is slow to accept
     connections on startup, readiness flaps.
  2. Liveness timeout too aggressive → container killed and restarted under load.
  3. OOMKill from a memory limit set too low.
- **Lesson.** Readiness gates traffic; liveness gates restarts; they are not
  interchangeable; k8s does **not** roll back a Deployment just because readiness fails;
  limits have teeth.
- **Roadmap ref.** 8.

### Beat 3.4 — The stateful decision

- **Trigger.** Dan: "Do we really want to be running our own database in the cluster?"
- **Build.** A short written decision (`docs/decisions/`): managed vs. in-cluster Postgres,
  tradeoffs (backups, failover, upgrades, expertise, cost, blast radius).
- **Complication.** None — this is a judgement beat.
- **Lesson.** Not every workload belongs in Kubernetes. Decision for the exercise: run
  in-cluster with a PVC **to learn the primitives**, with an explicit note that production
  would use a managed service.
- **Roadmap ref.** 9.

### Beat 3.5 — StatefulSet + PVC

- **Trigger.** Following 3.4: give Postgres real storage.
- **Build.** Postgres as a `StatefulSet` with a `volumeClaimTemplate`; headless Service.
- **Complication.** Data survives Pod deletion but not `kubectl delete pvc`; scaling a
  StatefulSet down leaves PVCs behind; ordering guarantees.
- **Lesson.** Pods are ephemeral; storage lifecycle is separate and deliberately sticky;
  what a StatefulSet does and does *not* solve (no automatic replication/failover).
- **Roadmap ref.** 10.

### Beat 3.6 — Multiple checker replicas

- **Trigger.** Checker throughput is too low for the number of monitors.
- **Build.** Scale `checker` to N replicas; add a claim query
  (`SELECT ... FOR UPDATE SKIP LOCKED`) so each due check is taken by exactly one replica.
- **Complication.** Before the claim query: double-probing returns, now in-cluster; a
  monitored team complains again.
- **Lesson.** Horizontal scaling of a worker needs a coordination mechanism; DB-level
  locking vs. leader election vs. a queue — tradeoffs.
- **Roadmap ref.** 11.

---

## Act 4 — CI/CD and the failure gauntlet

### Beat 4.1 — The pipeline

- **Trigger.** Priya: "Manual `kubectl apply` doesn't scale — let's build the pipeline."
- **Build.** GitHub Actions: run tests → build image → push to GHCR with an immutable tag
  (git SHA) → update the manifest → `kubectl rollout` → verify.
- **Complication.** A pipeline that pushes `latest` and a Deployment that doesn't change
  its image reference → "why didn't my change deploy?"
- **Lesson.** source → build artifact → image → container → Deployment → Pod, as distinct
  things; immutable tags; why `latest` breaks rollout and rollback.
- **Roadmap ref.** 12.

### Beat 4.2 — Ship, then roll back

- **Trigger.** Marta: "Send a webhook when an incident opens." (v1.1 — a real feature.)
- **Build.** The webhook feature, shipped through the pipeline as a rolling update.
- **Complication.** v1.2 ships a broken config value → rolling update, some Pods come up
  bad, `/status` degraded for a fraction of traffic → `kubectl rollout undo`.
- **Lesson.** Rolling update mechanics (surge/unavailable); partial failure during rollout;
  k8s does not auto-roll-back; how to roll back deliberately and what state the DB is left
  in.
- **Roadmap ref.** 13.

### Beat 4.3 — The gauntlet

Each sub-beat is an independent incident. The learner forms a diagnosis *before* the cause
is confirmed. Root causes are deliberately spread across categories.

| Version | Symptom | Root cause | Correct diagnosis |
|---------|---------|-----------|-------------------|
| **v2.0** | HTTP 500s on `/status` | Incident-close logic throws on a null `resolved_at` | The application is broken. Not Kubernetes. |
| **v2.1** | Pods flap Ready/NotReady, traffic drops | `/health/ready` was changed to also check a flaky external dependency | The readiness probe / config is wrong. The app is fine. |
| **v2.2** | `api` returns 503, `checker` in `CrashLoopBackOff` | Postgres PVC full / Pod evicted | A dependency is down. Beacon is behaving correctly. |
| **v2.3** | Behaviour differs between Pods for the "same" version | A stale ReplicaSet still serving / a node with an old cached image | Not all Pods are running what you think. |

- **Roadmap ref.** 14.

---

## Cross-cutting stakeholder churn

Dropped into the acts where they bite hardest, not run as a separate phase.

| Churn | Where it lands | Point |
|-------|----------------|-------|
| Marta redefines "degraded" after it's built | After 1.2 or 3.3 | Requirements change post-implementation; estimate the cost of the change. |
| Priority flip: urgent feature mid-Kubernetes work; Priya pushes back on infra debt | Mid Act 3 | Competing priorities; making the tradeoff explicit to stakeholders. |
| Ambiguous ask: "make it faster" | Act 3 or 4 | Which component? Clarify before acting — checker throughput vs. API latency are different problems. |
| Marta wants a feature that turns out to have deployment implications | Act 3 or 4 | "Simple" changes are not always simple once deployed. |

---

## Open questions / to decide

- Container registry: GHCR assumed. Confirm.
- Migrations tool: Alembic assumed. Confirm.
- Do we ever actually introduce a second environment (staging), or stay single-environment?
- How far to take observability (structured logging only, or a metrics endpoint too)?
