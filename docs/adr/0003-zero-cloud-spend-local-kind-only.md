---
Status: accepted
Date: 2026-09-09
---

# 0003. Zero cloud spend — everything runs locally on kind

The project must not cost money. Every environment therefore runs on **local kind
clusters**, the repository is **public** so GitHub Actions minutes and GHCR are free, and
there are **no managed cloud services** anywhere.

## Consequences

- Kubernetes is kind, not EKS/GKE/AKS.
- PostgreSQL runs in-cluster (see ADR-0005 and Beat 3.4), because a managed database costs
  money — even though a real shop on any budget would use RDS / Cloud SQL. Beat 3.4 keeps
  the managed-vs-self-hosted *reasoning* as an explicit exercise; only the outcome is
  constrained.
- The container registry is GHCR (free for public repos).
- The laptop pays the cost instead: three kind clusters is RAM-hungry.
