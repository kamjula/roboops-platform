# Changelog

## Phase 13 - Alert lifecycle (2026-09-18)

- Added authenticated alert listing with open/resolved/all and severity filters.
- Added idempotent operator/admin alert resolution with viewer write protection.
- Replaced the Alerts placeholder with a role-aware operational table and tested loading, error, empty, filter, resolution, and mutation-failure states.

## Phase 12 - Reproducible recruiter readiness (2026-09-18)

- Reconciled the public roadmap and security documentation with the implemented Phase 6-11 system.
- Added the frontend dependency lockfile and changed CI to `npm ci` for reproducible installs.
- Removed duplicate backend CI database bootstrap logic.
- Documented honest current capabilities and remaining production limitations.

All notable changes to this project are documented in this file. This project uses phase-based milestones instead of semantic versioning until the first tagged release exists.

## Phase 4 - Dashboard APIs (2026-08-05)
### Added
- Six read-only fleet dashboard endpoints under /api/v1/dashboard/*: summary, robot-status, latest-alerts, health-summary, site-summary, maintenance-summary
- Typed Pydantic response schemas for all dashboard endpoints
- Dashboard service layer with aggregation queries
- Test coverage for the dashboard API

## Phase 3 - Core CRUD APIs (2026-08-02)
### Added
- Full CRUD (create, list, get, update, delete) endpoints for robots, robot_models, and sites under /api/v1/*
- Typed request/response schemas and service-layer exception handling (404/409/422)
### Fixed
- Skipped DB-dependent API tests when TEST_DATABASE_URL is not set

## Phase 2 - Database Foundation (2026-07-30)
### Added
- SQLAlchemy 2.x models and Alembic migrations for all nine domain tables
- Deterministic, idempotent seed script (backend/scripts/seed.py)
- Dedicated ORM and migration test databases with transactional test isolation
- CI job (backend-db-tests) running against a live Postgres service
### Documentation
- Full column-level schema documentation in docs/database-schema.md

## Phase 1 - Initial Architecture
### Added
- React + Vite frontend scaffold
- FastAPI backend scaffold with a health endpoint
- Docker Compose setup for backend, frontend, and PostgreSQL
- Starter test suite

---
Note: entries above were reconstructed from the actual commit and CI history in this repository. No version tags exist yet in this repository; creating them (e.g. v0.4.0 for the current head) is a recommended next step.
---
Note: entries above were reconstructed from the actual commit and CI history in this repository. No version tags exist yet in this repository; creating them (e.g. v0.4.0 for the current head) is a recommended next step.
