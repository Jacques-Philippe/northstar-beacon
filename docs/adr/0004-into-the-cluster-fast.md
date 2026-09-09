---
Status: accepted
Date: 2026-09-09
---

# 0004. "Into the cluster fast" teaching sequence

The learning goal is Kubernetes and deployment-lifecycle fluency, so a deliberately trivial
version of Beacon is deployed to a kind cluster by **Beat 1.3** — before Postgres, config
management, or the checker split. From then on every change ships the same way (edit → build
image with an immutable tag → load into kind → update manifest → `kubectl rollout` →
observe), and new capabilities are layered onto an app that is *already running in the
cluster*.

## Considered options

- **Build up locally first** (the original brief: app → Postgres → Compose → *then*
  Kubernetes) — rejected: spends the first third of the project with zero `kubectl`
  exposure, which is backwards for someone whose explicit weakness is Kubernetes.
- **Into the cluster fast** — chosen: maximises reps in the cluster; the deployment loop
  becomes the spine of the course; painful lessons (e.g. losing in-memory state) are felt
  as real Pod reschedules rather than described.

## Consequences

The roadmap in `README.md` and the beats in `docs/narrative.md` are ordered around this.
