---
Status: accepted
Date: 2026-09-09
---

# 0007. CI-driven promotion; build once, promote the artifact

An image is **built once**, on merge to `master`, tagged with the immutable git short SHA,
and pushed to GHCR. Merging to `master` auto-deploys that image to **dev**. Promotion to
**staging** and then **prod** is a gated GitHub Actions `workflow_dispatch` (GitHub
Environments with a required reviewer) that **re-points the target overlay's image tag at
the already-built, already-tested image** — no rebuild. Promotion is recorded as a commit
bumping the overlay tag, so the repository is the source of truth for what is deployed
where.

## Considered options

- **Manual `kubectl apply` per environment** — rejected: not auditable, and the CI/CD
  pipeline is a committed deliverable of the project.
- **GitOps (Argo CD / Flux)** — rejected for now: large new surface area. A strong optional
  later beat.
- **Rebuild per environment** — rejected: breaks the guarantee that staging and prod run
  the exact artifact that passed tests.

## Consequences

No imperative `kubectl set image`. Rollback is re-pointing the overlay at a previous tag
(exercised in Act 4).
