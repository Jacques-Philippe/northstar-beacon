---
Status: accepted
Date: 2026-09-09
---

# 0011. A separate Vue frontend image, reached through an Ingress

Beacon gets a browser UI: a **Vue single-page app** (Vite), built as its **own container
image** via a multi-stage build (`node` build stage → static `dist/` served by `nginx`),
deployed as its own `Deployment` + `Service`, and exposed — alongside `api` — through a
single Kubernetes `Ingress`. It is introduced in Beats 2.2–2.3 of `docs/narrative.md`.

## Context

Michael wants a page he can show in a demo; the JSON API is not presentable. Separately,
the project is a portfolio piece — a running UI is far more legible to a visitor than
`kubectl` output. The application is meant to stay small (ADR-0002), so adding a frontend
is a deliberate trade against that principle, taken because the extra Kubernetes surface
(a second workload, an Ingress controller, multi-stage builds, runtime config injection)
is itself on-topic for a deployment-lifecycle project.

## Considered options

- **Server-rendered HTML from the `api` process** — rejected. Smallest change and no new
  image, but it teaches nothing new: no second workload, no Ingress, no browser-to-cluster
  wiring. It also couples a UI change to an `api` rollout.
- **Vue SPA served by the `api` process** (static files baked into the api image) —
  rejected. Keeps one image but still couples frontend and backend releases, and skips the
  Ingress/second-Service lesson that is the reason to do this at all.
- **Vue SPA as its own image, behind an Ingress** — chosen. A second Deployment/Service, an
  Ingress routing `/` to the frontend and `/api` to `api` on one origin, and an Ingress
  controller installed into kind. Most moving parts, most relevant to the project.
- **A build-tooling-free frontend** (hand-written HTML + vanilla JS) — rejected. Would keep
  the app smaller, but a Vue/Vite artifact is the more recognisable portfolio piece and
  brings the multi-stage build and build-time-vs-runtime-config lessons with it.

## Consequences

- A third thing to build and version. The frontend image is tagged with the git short SHA
  like `api`/`checker` and promoted the same way (ADR-0007) — never rebuilt per environment.
- The Ingress becomes the single entry point; `kubectl port-forward` stops being the normal
  way in. An Ingress controller (`ingress-nginx`) is now a required cluster component,
  provisioned from the `Makefile` with `extraPortMappings` in the kind config.
- Same-origin routing (`/` and `/api` under one host) means the SPA uses a **relative
  `/api`** base URL and needs no CORS config in `api`.
- Build-time config does not survive promotion: anything the SPA needs that differs per
  environment must be delivered at **runtime** — `nginx` serves a `/config.json` populated
  from a per-environment `ConfigMap` at container start (Beat 4.2). `vite build` output
  stays environment-agnostic.
- `k8s/` gains `frontend` and `ingress` manifests; the Act 4 kustomize overlays
  (ADR-0006) vary the frontend image tag and the Ingress host per environment
  (`beacon.dev.local` / `beacon.staging.local` / `beacon.prod.local`).
- The `pyproject.toml`/pytest inner loop now sits next to a `package.json`/Vite/`vitest`
  one; CI grows a frontend build and test alongside the `test` check.
- `node` and `npm` join the toolchain; `CONTEXT.md` gains **frontend** as a named
  component.
