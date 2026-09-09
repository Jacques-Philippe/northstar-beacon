---
Status: accepted
Date: 2026-09-09
---

# 0001. How this project is run and documented

Beacon is a Kubernetes and deployment-lifecycle learning exercise run as a **simulation of a
real project over time**: Jacques is the developer, and the stakeholders (Michael the Product
Owner, Andy on infrastructure, Stanley the engineering manager) are roleplayed, delivering
requirements and narrating realistic failures to diagnose. We document it the way a real
project would be, so that the artefacts themselves are part of the practice.

## Document roles

- **`README.md`** — what Beacon is, its current domain model and API, and an Act-level
  summary of the arc. It does **not** carry the beat list, to avoid drift against the script.
- **`CLAUDE.md`** — working conventions and repo settings.
- **`docs/narrative.md`** — the director's script: the planned beat-by-beat arc, and the
  roadmap of record. Amended in place when a beat diverges from the script.
- **`docs/adr/`** — architecture decision records. One decision per file,
  `NNNN-slug.md`, sequential numbering, minimal template (1–3 sentences) plus a `Status`
  frontmatter line. Superseded ADRs are kept and marked, not deleted.
- **`CONTEXT.md`** — the domain glossary (canonical terms only, no implementation detail).

## Consequences

A future reader encountering fictional people in `narrative.md` or an `InMemoryStorage`
class in a Kubernetes project should read the ADRs first; the decisions are deliberate and
recorded.

There is no standalone journal or changelog. The record of what actually happened is the
git history, the merged pull requests, and the closed issues — the same artefacts a real
project leaves behind. Diagnosis detail worth keeping goes in the PR body.
