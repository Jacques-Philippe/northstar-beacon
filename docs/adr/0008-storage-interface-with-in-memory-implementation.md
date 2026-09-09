---
Status: accepted
Date: 2026-09-09
---

# 0008. A storage interface with an in-memory implementation

Data access goes through a narrow `Storage` protocol (CRUD methods for `Monitor`,
`CheckResult`, `Incident`). Beat 1.1 ships `InMemoryStorage`; Beat 2.3 adds
`PostgresStorage` (SQLAlchemy) and switches the wiring.

## Why (this looks like premature abstraction)

The in-memory → Postgres swap is a **scheduled, known** requirement in the narrative, not
speculation, so the seam pays for itself immediately. It also keeps the unit-test suite
fast (in-memory) while integration tests exercise Postgres.

## Consequences

Kept deliberately minimal — no generic repository framework, no unit-of-work. If the
interface starts leaking SQL concepts, that's the signal it has outlived its purpose.
