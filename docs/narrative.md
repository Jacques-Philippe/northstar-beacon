# Beacon — Narrative Script

The planned story arc for the Beacon simulation. This is the **director's script**: it is
allowed to be known to the learner. Knowing the arc does not spoil the exercise — the
moment-to-moment work (writing code, reading logs, forming a diagnosis before the answer is
given) is where the learning happens. Individual failures are still revealed gradually
within a beat.

Keep this document in sync as beats are played, amended, or reordered — when a beat diverges
from the script, edit the beat here to match what actually happened. The running record of
what happened is the git history, the merged PRs, and the closed issues; decisions that were
a real trade-off go in `docs/adr/`.

## Design principle: into the cluster fast

The goal of the project is Kubernetes and deployment-lifecycle fluency, so the learner is
deploying to a local **kind** cluster by **Beat 1.3** — with a deliberately trivial app.
From that point on, *every* change ships the same way:

> edit code → build image with an immutable tag → load into kind → update the manifest →
> `kubectl rollout` → observe

New capabilities (history, a Vue frontend and an Ingress, Postgres, config, probes,
splitting the checker, StatefulSets, CI/CD) are then layered on top of an app that is
*already running in the cluster*. The
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
- **Complication** — a realistic *operational* problem: correct build, system still
  misbehaves. Not revealed all at once; the learner investigates. Only beats with such a
  problem carry this field.
- **Checkpoint** — what the learner is questioned on before the PR merges. Every beat
  carries one, whether or not it has a live Complication. See the note below.
- **Lesson** — the intended takeaway.
- **Roadmap ref** — this beat's number in the overall arc (1–22). `README.md` carries only
  an Act-level summary; this file is the roadmap of record.

Failures are deliberately varied in root cause: application bug, Kubernetes/config error,
database/dependency failure, or the monitored target genuinely being down.

### How complications and assessment work with an LLM in the loop

The learner pair-programs with an LLM, so "you wrote a subtle bug, now debug it" does not
happen by accident — the code arrives correct — and any mechanism that asks the learner to
*write something* (a prediction, a design note, the PR body) is defeated the same way.
See ADR-0012.

- **Operational complications stay.** The build is correct and the system still misbehaves
  because of how the pieces fit together (image never loaded into kind, a Service
  `targetPort` mismatch, a stale ReplicaSet, the wrong `kubectl` context). Diagnosed **live
  under gauntlet rules**: while the learner is diagnosing, Claude answers only *as the
  system would* — logs, `kubectl describe`, events, metric values in response to the right
  question — and does **not** volunteer the diagnosis. This is the Beat 4.4 model applied
  throughout, and it holds whenever the learner is mid-diagnosis.
- **Every beat ends with a Checkpoint.** After the code is done and **before the PR
  merges**, Claude questions the learner on what was built, why, and what would break — one
  question at a time, waiting for each answer before asking the next, ~4–6 in total. The
  learner answers in chat, cold — no reading the diff first, no help. Claude then assesses:
  for each item it shows the question, the learner's answer, and the verdict / correct
  answer together, so nothing has to be scrolled to. Weak answers are re-run.
  **A weak checkpoint blocks the merge.** Claude records the exchange as a *Checkpoint*
  section in the PR body (each question with a one-line verdict, gaps found and closed).
  Gauntlet rules apply during it: Claude asks and assesses, it does not teach.

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
- **Checkpoint.** No live complication this beat. Questioning covers: why storage sits
  behind a narrow protocol and what `InMemoryStorage` buys now versus costs later; how
  "current status" is *derived* from the latest check rather than stored on the monitor;
  liveness vs. readiness and why both are 200 stubs at this stage; why the checker runs
  in-process inside the API for now and what that choice will later force; what structured
  JSON logging gives you that ad-hoc prints do not.
- **Lesson.** Shape of the app; what liveness vs. readiness will come to mean; why the
  storage seam exists.
- **Roadmap ref.** 1.

### Beat 1.2 — Containerise

- **Trigger.** Andy: "If you want this anywhere near the cluster it needs to be an image."
- **Build.** Multi-stage `Dockerfile` (`uv` resolves the venv in a build stage; a slim,
  non-root runtime stage carries only Python and the venv), `.dockerignore`, and a
  `python -m beacon <api|checker>` entrypoint so one image serves both processes — the
  container command selects. `Makefile` targets tag the image with the git short SHA
  (no `latest`). Build and run both entrypoints under Docker; confirm the API answers on
  the published port and the checker starts its loop.
- **Checkpoint.** No live complication this beat. Questioning covers: source vs. build
  artifact vs. image vs. container; why the app must bind `0.0.0.0` and not `127.0.0.1`,
  and how that failure would present; what a runtime dependency left in the dev group does
  at `docker run` time versus at build time; `containerPort` / published-port / app-listen
  mismatch; what the build context is and why `.dockerignore` and layer ordering
  (`pyproject.toml` / `uv.lock` before the source) matter; what the multi-stage split buys
  and what is in the runtime image versus the build stage.
- **Lesson.** Source vs. build artifact vs. image vs. container. Build context and layer
  caching. Why the container environment differs from the laptop. Multi-stage builds: the
  build toolchain does not ship in the runtime image.
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
- **Checkpoint.** Questioning covers: Deployment vs. ReplicaSet vs. Pod and which object you
  actually edit; what a Service is and how it selects its Pods (labels), plus what
  `port-forward` does that a ClusterIP does not; why `ImagePullBackOff` happens in kind and
  how `kind load docker-image` differs from a registry pull; `containerPort` vs. Service
  `port` / `targetPort` vs. the port the process listens on, and which mismatch produces
  which symptom; what `kubectl describe` and events tell you that `get` does not; what
  "desired state → controller → actual state" means concretely for this deploy.
- **Lesson.** Desired state → controllers → actual state. Pod / ReplicaSet / Deployment /
  Service and how they relate. How an image gets to a node in kind.
- **Roadmap ref.** 3.

### Beat 1.4 — The deploy loop becomes routine

- **Trigger.** Michael: "Small thing — can each monitor record which team owns it?"
- **Build.** Add `owning_team` to `Monitor`. Ship it: rebuild the image with a new SHA tag,
  update the manifest's image reference, `kubectl apply`, watch `kubectl rollout status`.
- **Complication.** If the learner reuses a tag or edits in place: the rollout does nothing
  visible / Pods don't restart. Surfaces why immutable tags matter.
- **Checkpoint.** Questioning covers: what actually changes in the cluster when you apply a
  new image tag — the ReplicaSet swap the Deployment controller performs; why reusing a tag
  or `latest` makes the rollout a no-op and rollback impossible; what `kubectl rollout
  status` is waiting on; `maxSurge` / `maxUnavailable` at a high level; how you would revert
  this specific change and why that is just another forward apply.
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
- **As played (#10).** Built against `InMemoryStorage` only — SQLAlchemy/Alembic stay in
  Beat 2.5, so there is no migration yet. Settled decisions: threshold `N` is
  `BEACON_INCIDENT_FAILURE_THRESHOLD` (default 3), recovery is asymmetric (first success
  closes); `Incident.opened_at` is **backdated to the first failure** in the run, found by
  walking back over `CheckResult`s (survives a checker restart, unlike in-memory streak
  state); uptime is `1 − clipped incident downtime / window`; a disabled monitor's open
  incident is left open. `/monitors/{id}/results` deferred to a later beat.
- **Complication.** None yet — the trap is set in 2.4.
- **Checkpoint.** Questioning covers: why uptime is derived from incidents rather than
  scanning every `CheckResult`; what makes `CheckResult` append-only and why that matters;
  the incident state machine (opens after N consecutive failures, closes on recovery) and
  its edge cases — a flap, a failure at the boundary, a monitor disabled mid-incident; what
  `/status` aggregates and from where.
- **Lesson.** Deriving uptime from incidents rather than scanning every result.
- **Roadmap ref.** 5.

### Beat 2.2 — A page for the demo

- **Trigger.** Michael: "The JSON is fine for you. I can't pull up a page of raw API
  responses in front of anyone. I need something I can show in a demo — a list of what
  we're watching, green or red, the uptime numbers, recent incidents."
- **Build.** A **Vue single-page app** (Vite), read-only: renders `/monitors`, `/status`,
  and `/incidents`. Its own container image — a **multi-stage build** (`node` build stage →
  static `dist/` copied into an `nginx` image) — and its own `Deployment` (1 replica) and
  `Service`, separate from `api` (ADR-0011). No Ingress yet: the app is reached with one
  `kubectl port-forward` for the page and a second for the API, and the build takes the API
  base URL from `VITE_API_URL` pointed at that second forward.
- **Complication.** The two-port-forward setup is the problem. The API base URL is only
  correct because a forward happens to be running on that exact port; drop it or change the
  port and every call fails. Page and API are now different origins, so the browser blocks
  responses until CORS headers are added to `api` — configuration that exists only to prop
  up the port-forward workaround. Forwards die silently when a Pod restarts mid-demo.
- **Checkpoint.** Questioning covers: why the frontend is its own image, Deployment, and
  Service rather than served from `api` (ADR-0011); what the multi-stage build buys here —
  the `node` toolchain does not ship in the `nginx` runtime image; why a browser cannot use
  cluster DNS or Service names; same-origin vs. cross-origin and why CORS headers on `api`
  became necessary the moment there were two origins; why the two-port-forward setup is
  fragile and exactly what real infrastructure it is standing in for.
- **Lesson.** A browser is a client that lives outside the cluster and cannot resolve
  cluster DNS. Same-origin vs. cross-origin. A frontend Pod is easy; wiring a browser to
  reach two Services is not. Multi-stage image builds: the build toolchain does not ship in
  the runtime image.
- **Roadmap ref.** 6.

### Beat 2.3 — One front door

- **Trigger.** Andy: "Two port-forwards to look at one app is ridiculous. Put an Ingress in
  front of it."
- **Build.** Install an Ingress controller (`ingress-nginx`) into the `beacon-dev` kind
  cluster — `Makefile` target plus `extraPortMappings` in `kind/dev.yaml` so a laptop port
  reaches the controller. One `Ingress`: `beacon.dev.local/` → the frontend `Service`,
  `beacon.dev.local/api` → the `api` `Service`, with a `/api` prefix strip. A `beacon.dev.local`
  entry in `/etc/hosts` (the `.dev.` is deliberate — staging and prod hosts arrive in
  Act 4). The Vue app switches to a **relative `/api`** base URL — same
  origin — so the baked-in `VITE_API_URL` and the CORS headers from Beat 2.2 both go away.
  Note for later: anything genuinely per-environment in the frontend build returns in Act 4.
- **Complication.** kind routes nothing until the `extraPortMappings` and the controller
  line up. A path-rewrite mistake so `beacon.dev.local/api/monitors` reaches `api` as
  `/api/monitors` (404) instead of `/monitors`. A 404 that is the Ingress, not the app.
- **Checkpoint.** Questioning covers: Pod → Service → Ingress and what each layer routes on
  (L4 address/port vs. L7 host/path); the difference between an `Ingress` object (inert
  rules) and an Ingress controller (proxy Pods that read them); how kind gets outside
  traffic to the controller at all (`extraPortMappings`); what the `/api` prefix strip does
  and how a rewrite mistake yields a 404; how to tell an Ingress 404 from an app 404; why
  collapsing to one origin *removes* the CORS / `VITE_API_URL` problems rather than working
  around them.
- **Lesson.** Pod → Service (stable internal address) → Ingress (HTTP routing from outside
  to Services). An Ingress object is inert rules; an Ingress controller is just Pods running
  a reverse proxy. Collapsing two entry points to one origin removes a class of problems
  (CORS, per-client URLs) rather than working around them.
- **Roadmap ref.** 7.

### Beat 2.4 — Pods are ephemeral

- **Trigger.** After the next rollout (or a `kubectl delete pod`), Michael: "Why is all our
  uptime history back to 100%? We had an incident logged this morning."
- **Build.** Nothing new to build — this beat is investigation and a decision. The learner
  should conclude that in-memory state cannot live in a Pod.
- **Complication.** Every rollout and every rescheduled Pod wipes all history.
- **Checkpoint.** Questioning covers: where the "lost" history actually lived and why every
  rollout and reschedule wipes it; "cattle, not pets" and Pod disposability as a design
  choice, not a bug; why this forces an external database rather than a bigger Pod, node
  affinity, or a local volume; what would and would not survive each of — `kubectl delete
  pod`, a Deployment image bump, a node reboot.
- **Lesson.** Pods are disposable by design; application instances are cattle. State that
  must survive a Pod cannot live inside one. This is the forcing function for a database.
- **Roadmap ref.** 8.

### Beat 2.5 — PostgreSQL

- **Trigger.** Following 2.4: give Beacon somewhere durable to write.
- **Build.** Add a `PostgresStorage` implementation of the `Storage` protocol — SQLAlchemy
  2.0 ORM, synchronous, typed models (ADR-0009). Docker Compose runs Postgres for the local
  dev inner loop. In the cluster, Postgres runs as a `Deployment` with an `emptyDir` volume
  for now (**deliberately naive** — still not durable; this is the setup for Act 3). The app
  reads its connection URL from the environment.
- **Complication.** "Works in Compose, fails in kind": the DB host is still `localhost`
  instead of the Postgres `Service` name; or the app starts before Postgres accepts
  connections and crashes once.
- **Checkpoint.** Questioning covers: how the `Storage` protocol lets `PostgresStorage` drop
  in without touching call sites; why "works in Compose, fails in kind" — `localhost` vs. a
  Service name and how cluster DNS resolves it; what happens when the app starts before
  Postgres is ready and why a single crash-and-restart is acceptable here; why the
  `emptyDir` volume is *deliberately* not durable and what it sets up for Act 3; the
  sync-SQLAlchemy-in-a-threadpool tradeoff (ADR-0009).
- **Lesson.** Cluster DNS and Service names. The app now has a dependency it doesn't
  control the lifecycle of. Swapping a `Storage` implementation without touching call sites.
- **Roadmap ref.** 9.

### Beat 2.6 — Config out of the image

- **Trigger.** Andy: "The DB connection details are baked into the image. That's not going
  to fly once there's more than one environment."
- **Build.** `ConfigMap` for non-secret config (DB host, port, name, check defaults, log
  level); `Secret` for the DB username/password, created out-of-band by a bootstrap script
  and never committed (sealed-secrets is an *Optional later beat*). Wire both into
  the Pod via env. Manifests stay flat for now — the kustomize base/overlay restructure
  comes with the second environment in Beat 4.2.
- **Complication.** A wrong value in the ConfigMap (DB host typo) → `CrashLoopBackOff`.
  Diagnose from `kubectl describe`, logs, and the restart count / backoff.
- **Checkpoint.** Questioning covers: ConfigMap vs. Secret — what each is for and what is
  actually "secret" about a Secret (base64 is not encryption); how each reaches the Pod (env
  vs. mounted volume) and which changes are redeployable without a new image; why a bad
  config value presents identically to a bad app until you read the logs; how
  `CrashLoopBackOff` and the growing restart backoff show up in `kubectl describe`; why the
  Secret is created out-of-band and never committed, and what sealed-secrets would change.
- **Lesson.** Config is separate from the image and separately deployable. A bad config
  presents identically to a bad app until you read the error.
- **Roadmap ref.** 10.

### Beat 2.7 — Migrations

- **Trigger.** A schema change is needed — e.g. an index on `check_result (monitor_id,
  checked_at)` because `/uptime` has gotten slow, or a new nullable column.
- **Build.** Wire up Alembic (ADR-0009); a baseline migration for the existing schema; the
  change as a second migration. Run migrations as a Kubernetes `Job` (or init container)
  ordered before the new Pods roll.
- **Complication.** A migration that succeeds against an empty dev database behaves badly
  against realistic data: adds a `NOT NULL` column with no default, or takes a lock that
  blocks writes.
- **Checkpoint.** Questioning covers: why migrations run as a `Job` (or init container)
  ordered *before* the new Pods roll; forward/backward compatibility during a rolling update
  — old and new code coexisting for a window, and what schema changes that forbids (a bare
  `NOT NULL` add, a column rename); what locks a migration can take against real data that
  an empty dev DB hides; the baseline-migration concept; what happens to the rollout if the
  migration Job fails.
- **Lesson.** Migrations are code that runs against real data. Forward/backward
  compatibility during a rolling update (old and new code briefly coexist). Ordering of
  "migrate" vs. "new pods".
- **Roadmap ref.** 11.

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
- **Checkpoint.** Questioning covers: readiness gates traffic, liveness gates restarts —
  what breaks if you swap them; why a readiness probe that checks a flaky dependency causes
  flapping and dropped traffic; why too-short a liveness `timeoutSeconds` under load causes
  a restart loop; what Kubernetes does when the new Pods never go Ready during a rollout (it
  does **not** roll back — the old ReplicaSet stays and the rollout stalls); the roles of
  `initialDelaySeconds` / `periodSeconds` / `failureThreshold`.
- **Lesson.** Readiness gates traffic; liveness gates restarts; they are not
  interchangeable. Kubernetes does **not** roll back a Deployment just because the new Pods
  never become Ready — the old ReplicaSet stays up and the rollout simply stalls.
- **Roadmap ref.** 12.

### Beat 3.2 — Resource requests and limits

- **Trigger.** Andy: "Your Pods have no requests or limits. On a shared cluster that's how
  you get evicted at 3am."
- **Build.** Set `requests` and `limits` for CPU and memory on `api`, `checker`, and
  Postgres.
- **Complication.** A memory `limit` set too low → `OOMKilled`, visible in
  `kubectl describe` as the last state. Or `requests` set so high the Pod stays `Pending`
  with `FailedScheduling`.
- **Checkpoint.** Questioning covers: requests drive scheduling, limits are enforced hard —
  what each one actually does; what `OOMKilled` looks like in `kubectl describe` (last
  state) and what triggers it; what `Pending` / `FailedScheduling` means and how oversized
  requests produce it; CPU-limit throttling vs. memory-limit killing; how requests and
  limits map to QoS class and eviction order.
- **Lesson.** Requests drive scheduling; limits are enforced hard. What "the scheduler
  couldn't place this Pod" looks like.
- **Roadmap ref.** 13.

### Beat 3.3 — Scale the API, split the checker

- **Trigger.** Stanley: "Beacon itself can't be a single point of failure. Run more than
  one."
- **Build.** Scale `api` to 3 replicas. Observe that each replica runs its own in-process
  checker → every target is now probed 3×. Split the checker into its **own Deployment**
  (1 replica) and remove the loop from `api`.
- **Complication.** A monitored team messages: "Beacon is hitting our health endpoint every
  10 seconds, we configured 30."
- **Checkpoint.** Questioning covers: why `api` scales safely to 3 replicas but an
  in-process checker does not — N copies means every target probed N×; why a background
  worker is not stateless-by-nature the way a request handler is; the case for a separate
  `checker` Deployment with its own replica count; what a Service load-balances across and
  what keeps the `api` replicas interchangeable; what still breaks with a single checker
  (the setup for 3.6).
- **Lesson.** Stateless replicas behind a Service are easy. A background worker is not
  stateless-by-nature — running N copies changes behaviour. Separating workloads that scale
  differently.
- **Roadmap ref.** 14.

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
- **Checkpoint.** Questioning covers: the managed-vs-self-hosted Postgres axes — backups,
  failover, version upgrades, on-call expertise, blast radius, cost; why the project lands
  on in-cluster (the zero-spend constraint, ADR-0003) and why that is a *constraint-driven*
  decision, not the engineering-preferred one; what a real shop would do here; how the
  learner would defend this tradeoff to an interviewer without hand-waving.
- **Lesson.** Not every workload belongs in Kubernetes. Recognising when a constraint (not
  an engineering preference) is driving an architecture decision.
- **Roadmap ref.** 15.

### Beat 3.5 — StatefulSet and PVC

- **Trigger.** Following 3.4: replace the throwaway `emptyDir` Postgres with something
  durable.
- **Build.** Postgres as a `StatefulSet` with a `volumeClaimTemplate`; a headless Service.
  Verify data now survives a Pod delete.
- **Complication.** Data survives `kubectl delete pod` but not `kubectl delete pvc`;
  scaling the StatefulSet down leaves the PVC behind; the Pod comes back with a stable name
  and re-attaches its volume.
- **Checkpoint.** Questioning covers: what a StatefulSet gives you that a Deployment does
  not — stable identity, ordered rollout, per-Pod storage via `volumeClaimTemplate`; what it
  still does **not** give you (replication, failover, backups); why a PVC outlives a Pod
  delete and even a scale-down; the role of the headless Service; Pod lifecycle vs. storage
  lifecycle as deliberately separate, sticky things.
- **Lesson.** Pod lifecycle and storage lifecycle are separate, and storage is
  deliberately sticky. What a StatefulSet gives you (stable identity, ordered rollout,
  per-Pod storage) and what it does **not** (replication, failover, backups).
- **Roadmap ref.** 16.

### Beat 3.6 — Multiple checker replicas

- **Trigger.** The single checker can't keep up with the number of monitors; checks are
  falling behind their intervals.
- **Build.** Scale `checker` to N replicas; add a claim query
  (`SELECT ... FOR UPDATE SKIP LOCKED`) so each due check is taken by exactly one replica.
- **Complication.** Before the claim query: double-probing returns, now from multiple
  checker Pods; a monitored team complains again.
- **Checkpoint.** Questioning covers: why "just add replicas" is safe for `api` but not
  `checker`; how `SELECT ... FOR UPDATE SKIP LOCKED` makes each due check the property of
  exactly one replica; the alternatives — leader election, a real queue — and their
  tradeoffs; what double-probing looks like from the monitored team's side; what happens to
  a claimed check if that checker Pod dies mid-probe.
- **Lesson.** Horizontally scaling a worker needs an explicit coordination mechanism.
  DB-level locking vs. leader election vs. a real queue — the tradeoffs, and why "just add
  replicas" is safe for `api` but not for `checker`.
- **Roadmap ref.** 17.

### Beat 3.7 — A metrics endpoint

- **Trigger.** Andy: "When the checker fell behind, how would we have known before the
  monitored teams told us?"
- **Build.** A Prometheus `/metrics` endpoint on `api` (and the checker): check throughput,
  probe latency, queue depth / lag, incident counts. **No** Prometheus or Grafana
  deployment — the endpoint and a documented `kubectl port-forward` + `curl` is enough for
  the exercise.
- **Complication.** None required; optionally, a metric that lies (a counter reset on every
  scrape because it's per-request state).
- **Checkpoint.** Questioning covers: logs (events) vs. metrics (aggregates) and when you
  reach for each; what to instrument to catch "the checker is falling behind" before a team
  tells you — throughput, probe latency, queue depth / lag; why a counter that resets each
  scrape lies, and how Prometheus expects counters to behave (monotonic, read via `rate()`);
  why the `/metrics` endpoint plus a documented port-forward is enough without deploying
  Prometheus or Grafana.
- **Lesson.** Instrumentation as a first-class concern; the difference between logs (events)
  and metrics (aggregates); why you don't need the whole observability stack to get value.
- **Roadmap ref.** 18.

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
- **Checkpoint.** Questioning covers: the full chain source → build → image → registry →
  Deployment update → rollout → Pods, named at each hop; why the `test` check is required by
  `protect-master` and what that buys; why a pipeline that pushes `:latest` against a fixed
  image reference produces "CI green, nothing deployed"; what makes an immutable SHA tag
  auditable and reversible; what "auto-deploy to `beacon-dev`" actually does to the cluster.
- **Lesson.** The pipeline as: source → build artifact → image → registry → Deployment
  update → rollout → Pods. Immutable tags are what make that chain auditable and
  reversible.
- **Roadmap ref.** 19.

### Beat 4.2 — Staging and production

- **Trigger.** Stanley: "dev is not where we demo. Stand up staging and prod, and make
  releasing to them boring."
- **Build.**
  - Provision `beacon-staging` and `beacon-prod` kind clusters (`make staging-up`,
    `make prod-up`; `kind/staging.yaml`, `kind/prod.yaml`).
  - Restructure manifests into kustomize `base/` + `overlays/{dev,staging,prod}/` (ADR-0006).
    Overlays vary replica count, resource requests/limits, log level, image tag, and per-env
    Secret/ConfigMap values — for `api`, `checker`, the `frontend`, and the `Ingress` host
    (`beacon.dev.local` / `beacon.staging.local` / `beacon.prod.local`). Each environment
    gets its own isolated Postgres (ADR-0005).
  - Promotion (ADR-0007): merge → dev automatically; a gated `workflow_dispatch` (GitHub
    Environments, self-review) re-points the **staging** then **prod** overlay at the
    already-built, already-tested SHA tag — no rebuild. Each promotion is a commit bumping
    the overlay tag.
  - Seed each environment's `Monitor` rows separately (dev watches throwaway targets, prod
    watches "real" Northstar services) — target lists are DB data, not overlay config.
- **Complication.** "Works in dev, not in staging": an overlay patch typo, a Secret that was
  only ever created in the dev cluster, or a `kubectl` context left pointing at the wrong
  cluster. And the frontend: the *same* `frontend` image promoted from dev now needs a
  per-environment value it can't have — anything baked at `vite build` time is frozen into
  the image and can't differ per env without a rebuild, which ADR-0007 forbids. Fix it with
  **runtime config injection**: nginx serves a small `/config.json` (or an `envsubst`'d
  `config.js`) populated from a per-env `ConfigMap` at container start, and the app reads it
  on boot. The relative `/api` base URL from Beat 2.3 still needs no config; genuinely
  per-env values (labels, feature flags, external links) go through `/config.json`.
- **Checkpoint.** Questioning covers: build once / promote the artifact — why rebuilding per
  environment is wrong (ADR-0007); kustomize `base` vs. overlays, and what legitimately
  varies per env vs. what must be byte-identical; the danger of the ambient `kubectl`
  context; why a Secret created only in the dev cluster breaks staging; why build-time
  `vite` config cannot differ per env once the image is promoted, and how a runtime
  `/config.json` from a per-env ConfigMap fixes it; why the relative `/api` URL needs no
  config; why the `Monitor` target lists are DB data, not overlay config.
- **Lesson.** Build once, promote the artifact. `kubectl` contexts and the danger of the
  ambient one. What legitimately differs between environments vs. what must be identical.
  For a static SPA, build-time config breaks promotion — per-env config has to arrive at
  runtime, the same way it does for the backend.
- **Roadmap ref.** 20.

### Beat 4.3 — Ship, then roll back

- **Trigger.** Michael: "Send a webhook when an incident opens." (v1.1 — a real feature.)
- **Build.** The webhook feature, shipped through the pipeline: merge → dev, promote →
  staging → prod.
- **Complication.** v1.2 promotes a bad config value to prod → rolling update, some Pods
  come up broken, `/status` fails for a fraction of traffic → roll back by re-pointing the
  prod overlay at the previous tag.
- **Checkpoint.** Questioning covers: rolling update mechanics — `maxSurge` /
  `maxUnavailable` and what a partial failure mid-rollout looks like to a user; why
  Kubernetes does not auto-roll-back a bad config; rollback as re-pointing the overlay at a
  known-good SHA, not a rebuild; what state the database is left in after a partial rollout
  and why that is the harder question; how promotion staging → prod flows through
  `workflow_dispatch`.
- **Lesson.** Rolling update mechanics (`maxSurge` / `maxUnavailable`); partial failure
  mid-rollout; Kubernetes does not auto-roll-back; rollback is promoting a known-good
  artifact, not a rebuild; what state the database is left in.
- **Roadmap ref.** 21.

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

- **Checkpoint.** This beat *is* the checkpoint model at full strength: for each incident the
  learner states a diagnosis before the cause is confirmed, under gauntlet rules, and the
  "Correct diagnosis" column is the assessment key. Questioning also covers how the learner
  told the categories apart — application bug vs. probe/config error vs. dependency down vs.
  wrong-version-running — from `kubectl` evidence alone, and what single command would have
  disambiguated fastest in each case.
- **Roadmap ref.** 22.

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
