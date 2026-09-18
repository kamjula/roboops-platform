# Changelog

All notable changes are documented here. RoboOps follows semantic versioning
starting with the first tagged release.

## [0.1.0] - 2026-09-18

### Platform

- Added FastAPI, React/Vite, PostgreSQL, Alembic, Docker Compose, and production
  backend/Nginx frontend containers.
- Added full CRUD for sites, robot models, and robots, plus authenticated fleet
  dashboard and alert lifecycle workflows.
- Added JWT authentication, role-based access control, and a safe idempotent
  initial-user bootstrap command.

### Telemetry and analytics

- Added idempotent HTTP telemetry ingestion and a stateful synthetic simulator.
- Added Kafka/Redpanda producer and consumer flow with retry classification and
  dead-letter topic handling.
- Added telemetry health, deterministic anomaly rules, trend analytics,
  statistical anomaly scoring, feature extraction, training-readiness gates,
  and truthful unsupervised condition scoring.
- Added condition-to-alert synchronization with database deduplication and
  conservative unknown-signal handling.

### Operations and evidence

- Added Prometheus HTTP metrics, request IDs, structured correlation payloads,
  liveness/readiness checks, and low-cardinality route labels.
- Added isolated PostgreSQL/migration tests, Kafka E2E, production-container
  smoke tests, and Playwright Chromium authentication/operations workflows.
- Added reproducible dependency locks, CI container builds, synthetic seed
  data, security documentation, and explicit non-claims.

### Release artifacts

- Added automated version-tagged GHCR backend/frontend images with SBOM and
  provenance metadata.
- Added a versioned GitHub release created only after both images publish.

## Historical milestones

- Phase 13: authenticated alert lifecycle API and role-aware UI.
- Phase 12: reproducible builds and recruiter-facing evidence cleanup.
- Phases 1-11: platform foundation through truthful condition scoring.
