---
Status: accepted
Date: 2026-09-09
---

# 0009. SQLAlchemy 2.0 ORM (sync) and Alembic

`PostgresStorage` (ADR-0008) uses the **SQLAlchemy 2.0 ORM with typed models**, run
**synchronously** in FastAPI's threadpool, with **Alembic** for migrations.

## Considered options

- **Async SQLAlchemy** — rejected: more realistic for FastAPI but adds async-session
  footguns for little benefit at this size.
- **SQLModel** — rejected: too much magic over a still-young base.
- **Raw SQL** — rejected: maximises DB understanding but slows feature work, and the app
  isn't the point.
- **SQLAlchemy 2.0 sync ORM + Alembic** — chosen: what Jacques will meet in real jobs, and
  Alembic makes the migrations beat (2.5) first-class.

## Consequences

Alembic is a lock-in of sorts — migration history is tied to it. Acceptable; it's the
standard pairing.
