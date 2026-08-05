# Changelog

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
