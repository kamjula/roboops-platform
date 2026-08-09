# ADR 0001: Defer Authentication and RBAC to Phase 5

## Status
Accepted

## Context
Phases 1 through 4 implement the core domain model, migrations, core CRUD APIs, and read-only dashboard aggregate APIs for RoboOps. No route in any router currently requires authentication or authorization; all endpoints under /api/v1/* are open by design at this stage.

## Decision
Authentication and role-based access control will be implemented once, consistently, across every router in a dedicated Phase 5, rather than added incrementally per-router as new endpoints are built. Adding partial authentication now (for example, only on the dashboard endpoints) would create inconsistent behavior between endpoints and would likely require rework once a real identity/authorization approach (such as OAuth2/JWT via FastAPI's security utilities) is selected for the whole API.

## Consequences
Until Phase 5 ships, this API is not safe to expose on an untrusted network or with real, sensitive data. This limitation is documented in SECURITY.md and in the README's Honest Project Status section. Any deployment before Phase 5 should be restricted to a trusted network or placed behind a separate access-control layer (for example, a reverse proxy requiring authentication).

## Alternatives Considered
Adding authentication only to the new Phase 4 dashboard routes was considered and rejected, because it would leave the Phase 3 CRUD routes open while the newer dashboard routes were protected, an inconsistency with no clear justification and a confusing API contract for any consumer.
