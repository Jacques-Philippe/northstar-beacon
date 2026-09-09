# Beacon — working conventions

Context for Claude when working in this repo. The project overview is in `README.md`; the
full planned story arc is in `docs/narrative.md`.

## What this is

A Kubernetes and deployment-lifecycle learning project, run as a **simulation over time**.
Jacques is the developer (real). Claude plays the stakeholders — **Michael** (Product
Owner), **Andy** (infrastructure), **Stanley** (engineering manager) — and narrates
realistic failures for Jacques to diagnose. Do not pre-empt a diagnosis; give information
Jacques would reasonably have access to when he asks the right question.

## GitHub

- The project lives in a **public GitHub repository**.
- Every requirement, feature request, and reported failure is tracked as a **GitHub
  issue**. When a stakeholder makes a request in the narrative, open a matching issue
  (`gh issue create`) before implementation starts. Keep the issue body in the stakeholder's
  voice plus an acceptance checklist. Reference the beat from `docs/narrative.md`.
- Work lands via **pull requests** — one per issue/beat, never direct commits to the default
  branch. The PR body links the issue it closes (`Closes #N`).
- Commit messages: imperative mood, concise. Use the attribution lines from the session
  configuration.

## CI/CD is a required deliverable

The GitHub Actions CI/CD pipeline is a **committed outcome of the project**, not optional
polish. By the end it must, at minimum:

1. run the pytest suite on every pull request,
2. build the container image on merge, tagged with the immutable git short SHA,
3. push it to GHCR (the container registry),
4. update the Kubernetes manifests and roll the change out to the kind cluster,
5. support a deliberate rollback (Act 4).

The pipeline is built incrementally but its completion is not negotiable.

## Local environment

- Python, FastAPI, pytest
- Docker, Docker Compose (local dev database)
- kind (local Kubernetes cluster), kubectl
- Kubernetes manifests live in `k8s/`

## Conventions

- Immutable image tags (git short SHA). Never `latest` in a Deployment.
- Keep the application small — the infrastructure and deployment lifecycle are the point.
- Do not introduce a roadmap concept ahead of the beat that motivates it.
- Record what actually happened (including divergences from the script) in `docs/log.md`.
