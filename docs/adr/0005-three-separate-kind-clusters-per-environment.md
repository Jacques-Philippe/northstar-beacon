---
Status: accepted
Date: 2026-09-09
---

# 0005. Three separate kind clusters, one per environment

Beacon runs in three environments — `dev`, `staging`, `prod` — and each is its **own kind
cluster** (`beacon-dev`, `beacon-staging`, `beacon-prod`), switched via `kubectl` context.
Each cluster has its own isolated PostgreSQL (own StatefulSet and PVC); a bad migration in
one environment cannot touch another's data.

## Considered options

- **One cluster, three namespaces** — rejected: doesn't teach `kubectl` context switching
  or model the real prod isolation boundary (separate control plane, blast radius, RBAC).
- **Two clusters** (`dev`+`staging` together, `prod` separate) — rejected as a middle
  option; Jacques opted for maximum fidelity.
- **Three clusters** — chosen: exercises both context switching and per-environment
  isolation; "namespaces vs. separate clusters" is a common interview question and this
  forces living the answer.

## Consequences

- Higher laptop resource cost (three control planes).
- Cluster provisioning is scripted (`Makefile` + `kind/<env>.yaml`) so environments are
  reproducible.
- "Introduce staging as a namespace instead" remains available as an optional later beat if
  the resource cost bites.
