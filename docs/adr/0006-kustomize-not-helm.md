---
Status: accepted
Date: 2026-09-09
---

# 0006. kustomize, not Helm, for environment configuration

Per-environment manifests are managed with **kustomize**: a `base/` of plain Kubernetes
YAML plus `overlays/{dev,staging,prod}/` that patch it. Overlays vary replica count,
resource requests/limits, log level, image tag, and per-environment Secret/ConfigMap
values. The monitored-target list is **not** overlay config — it is runtime data in each
environment's database, seeded per environment.

## Considered options

- **Helm** — rejected for now: Go-templated YAML hides the primitives this project exists to
  teach, and adds a release-management layer before it's needed. "Package Beacon as a Helm
  chart" is a good optional later beat.
- **Raw per-environment directories** — rejected: guaranteed drift.
- **kustomize** — chosen: overlays are patches over real manifests, so every primitive
  stays readable.

## Consequences

`kubectl apply -k overlays/<env>` is the deploy primitive; promotion (ADR-0007) is a commit
that bumps an overlay's image tag.
