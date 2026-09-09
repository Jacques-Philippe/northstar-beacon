# Beacon — working conventions

Context for Claude when working in this repo. The project overview is in `README.md`; the
full planned story arc is in `docs/narrative.md`; settled decisions and their reasoning are
in `docs/adr/`; domain vocabulary is in `CONTEXT.md` (follow it — e.g. never write bare
"probe" for the Kubernetes concept).

## What this is

A Kubernetes and deployment-lifecycle learning project, run as a **simulation over time**.
Jacques is the developer (real). Claude plays the stakeholders — **Michael** (Product
Owner), **Andy** (infrastructure), **Stanley** (engineering manager) — and narrates
realistic failures for Jacques to diagnose. Do not pre-empt a diagnosis; give information
Jacques would reasonably have access to when he asks the right question.

## GitHub

- The project lives in a **public GitHub repository**: `Jacques-Philippe/northstar-beacon`
  (default branch `master`).
- Repository settings: **squash-merge only** (merge commits and rebase merging disabled),
  **head branches auto-deleted on merge**, squash commit uses the PR title and body.
  Interaction is limited to **collaborators only**.
- `master` is protected by the `protect-master` ruleset (no bypass actors): changes must go
  through a PR, review threads must be resolved, force-pushes and deletion are blocked, and
  the `test` status check must pass. The `test` check is produced by the CI workflow added
  in the first feature PR.
- Every requirement, feature request, and reported failure is tracked as a **GitHub
  issue**, opened before implementation starts, with the body in the stakeholder's voice
  plus an acceptance checklist and a reference to the beat in `docs/narrative.md`.
- **Confirm with Jacques before any outward-facing GitHub action** — creating an issue,
  opening a PR, pushing a branch to `origin`, or changing repo settings he did not name.
  Propose it and wait for a yes. Local work (commits on a feature branch, file edits) does
  not need a prompt.
- Work lands via **pull requests** — one per issue/beat, never direct commits to the default
  branch. The PR body links the issue it closes (`Closes #N`).
- Commit messages: imperative mood, concise. Use the attribution lines from the session
  configuration.

## CI/CD is a required deliverable

The GitHub Actions CI/CD pipeline is a **committed outcome of the project**, not optional
polish. By the end it must, at minimum:

1. run the pytest suite on every pull request (the `test` check),
2. build the container image on merge, tagged with the immutable git short SHA,
3. push it to GHCR (the container registry),
4. auto-deploy that image to the `dev` cluster,
5. promote the *same* image to `staging` then `prod` via a gated `workflow_dispatch`
   (build once — never rebuild per environment),
6. support a deliberate rollback by re-pointing an overlay at a previous tag (Act 4).

The pipeline is built incrementally but its completion is not negotiable.

## Local environment

- Python 3.12, `uv` + `pyproject.toml`, FastAPI, pytest
- SQLAlchemy 2.0 ORM (sync) + Alembic; `Storage` protocol with in-memory and Postgres
  implementations
- Docker, Docker Compose (local dev database only)
- Three kind clusters — `beacon-dev`, `beacon-staging`, `beacon-prod` — provisioned via the
  `Makefile` and `kind/<env>.yaml`
- Manifests: `k8s/base/` + `k8s/overlays/{dev,staging,prod}/` (kustomize)
- One image, two entrypoints: the container command selects `api` or `checker`

## Conventions

- Immutable image tags (git short SHA). Never `latest` in a Deployment.
- Keep the application small — the infrastructure and deployment lifecycle are the point.
- Do not introduce a roadmap concept ahead of the beat that motivates it.
- When a beat diverges from the script, amend the beat in `docs/narrative.md` to match what
  happened. There is no separate journal — git history, merged PRs, and closed issues are
  the record; put diagnosis detail worth keeping in the PR body.
- When a decision is hard to reverse, surprising, and the result of a real trade-off, write
  an ADR in `docs/adr/` (`NNNN-slug.md`, minimal template + `Status` frontmatter).
- Everything runs locally — no managed cloud services, no spend (ADR-0003).
