# Project log

A running journal of what *actually* happened — decisions taken, beats played, failures
hit and how they were diagnosed, and divergences from `docs/narrative.md`. Newest entries
at the bottom.

---

## 2026-09-09 — Planning

- Project scoped: Beacon, an uptime monitor, as the vehicle for a Kubernetes /
  deployment-lifecycle learning exercise. Ran a grilling session to settle the design.
- Wrote `README.md`, `CLAUDE.md`, `docs/narrative.md` (the beat-by-beat script).
- Public GitHub repo created: `Jacques-Philippe/northstar-beacon` (default branch
  `master`). Repo settings: squash-merge only, auto-delete head branches, interaction
  limited to collaborators. `protect-master` ruleset: PR required, `test` status check
  required, review threads must resolve, no force-push or deletion, no bypass actors.
- Recorded architecture decisions as ADR-0001 … ADR-0009 and created `CONTEXT.md`.
- Key decisions: three separate kind clusters (dev/staging/prod); kustomize base+overlays;
  CI-driven promotion, build-once; zero cloud spend; SQLAlchemy 2.0 sync ORM + Alembic;
  `Storage` protocol with an in-memory implementation first.
- Issue #1 opened for Beat 1.1 (not yet started).
- Branch `beat-1.1-minimal-service` holds the planning docs; it will also carry the Beat
  1.1 app skeleton + CI workflow and merge as a single PR.
