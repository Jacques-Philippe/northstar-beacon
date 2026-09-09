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

## 2026-09-09 — Beat 1.1 built

- Grilling session before implementation settled the open design points. Notable outcomes:
  - `owning_team` pulled out of Beat 1.1 (issue #1 amended) — adding it is Beat 1.4's payload
    for exercising the deploy loop.
  - Checker runs on **real wall-clock time** making **real `httpx` calls**; it lives as an
    asyncio task in the FastAPI lifespan (not a separate entrypoint yet — that's Beat 1.2).
    No ADR: this is the obvious reading of the existing brief.
  - Beat 1.1 keeps only the *latest* `Outcome` per monitor (transient); the append-only
    `CheckResult` entity is Beat 2.1.
  - `Prober` protocol mirrors the `Storage` seam so tests need no network.
  - Monitor `id` is a UUID4 string. JSON logging is stdlib + a ~20-line formatter, no dep.
  - `test` CI check = `ruff check` + `ruff format --check` + `pytest`.
- Shipped: `Monitor` CRUD (`GET/POST /monitors`, `GET/PATCH/DELETE /monitors/{id}`),
  derived `status` (up/down/unknown), `/health/{live,ready}` stubs, `InMemoryStorage`,
  in-process `Checker`, `pydantic-settings` config, `.github/workflows/ci.yml`, 19 tests.
- No `Makefile`/`kind/`/`Dockerfile` yet — their own beats.
