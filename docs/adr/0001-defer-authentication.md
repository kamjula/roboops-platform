# ADR 0001: Defer Authentication and RBAC to Phase 6

## Status
Accepted

## Context
Phases 1 through 5 implement the core domain model, migrations, CRUD APIs, dashboard aggregate APIs, and the platform baseline for RoboOps. No route in any router currently enforces role-based authorization; all existing routes remain intentionally open until the dedicated authentication foundation and later authorization layer are introduced.

## Decision
Authentication will be implemented first as a Phase 6 foundation with a reusable user model, password hashing, JWT access tokens, and a protected /auth/me identity endpoint. Role-based access control remains explicitly out of scope for this slice and will be layered in later once the identity foundation is stable. This avoids partial or inconsistent auth enforcement across the API while keeping the first implementation intentionally minimal.

## Consequences
Until Phase 6 is complete, this API must still be treated as unsuitable for untrusted networks. Existing routes remain open by design and do not yet enforce identity or authorization. Any deployment should still be restricted to a trusted network or placed behind a separate access-control layer until the later RBAC phase lands.

## Alternatives Considered
Adding route enforcement before establishing the identity foundation was rejected because it would force premature role checks on an incomplete user model and a partially established auth contract. The Phase 6 approach keeps the system consistent and reversible while leaving RBAC for a later, explicit phase.
