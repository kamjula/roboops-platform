# RoboOps recruiter demo guide

This guide is a short, repeatable walkthrough of evidence already present in
the repository and hosted demo. It does not add performance, accuracy, uptime,
or business-impact claims that have not been measured.

## Before the call

1. Open <https://roboops-platform.vercel.app> and select **Explore read-only
   demo**. Wake the Render free instance several minutes before the interview.
2. Keep the GitHub repository and the API documentation open in separate tabs.
   Confirm the CI and Security badges are green before presenting them.

## 90-second walkthrough

### 0–20 seconds: product and data boundary

> RoboOps is a full-stack fleet monitoring portfolio system. The hosted demo
> uses a bounded synthetic telemetry stream for 12 fictional robots, so I can
> demonstrate the complete workflow without claiming access to real customer
> data or real-world prediction accuracy.

Show the Dashboard. Point out the fleet summary and the separate trigger and
recorded timestamps on recent alerts.

### 20–45 seconds: telemetry and analytics

Open Telemetry, then Analytics.

> Readings enter through an idempotent FastAPI ingestion contract and are stored
> in PostgreSQL. The analytics workspace exposes threshold events, statistical
> baseline signals, bounded trend series, and fleet condition scores. The UI
> explicitly says these are anomaly signals—not failure probability or remaining
> useful life—because the project does not have labeled failure outcomes.

Two concrete implementation examples:

- A repeated telemetry event is handled through application-level idempotency
  instead of creating duplicate readings.
- The 24-, 72-, and 168-hour analytics windows use bounded API queries and date-
  aware labels rather than loading an unbounded history into the browser.

### 45–70 seconds: operations and access control

Open Alerts, Tasks, and Maintenance.

> Alerts are persisted records with an authenticated lifecycle. Tasks is an
> honest review queue derived from open alerts and maintenance schedules; it
> does not pretend a separate task-management backend exists. The public demo
> receives a short-lived viewer session and server-side RBAC blocks writes.

Two concrete security examples:

- Logout revokes the database-backed JWT session; CI verifies that the old
  token is rejected afterward.
- Login and telemetry-write endpoints return bounded rate-limit headers and
  `429` responses, while the README discloses that the limiter is process-local.

### 70–90 seconds: delivery evidence

Open the GitHub Actions page or point to the repository badges.

> The repository runs backend and PostgreSQL tests, frontend tests and build,
> a real Redpanda-to-PostgreSQL smoke path, production-container smoke tests,
> Chromium E2E, CodeQL, dependency audits, and container scans. The frontend is
> on Vercel, the API on Render, and PostgreSQL on Neon.

Finish with one explicit limitation:

> The next engineering step would be labeled failure data and time-aware model
> evaluation. Until that exists, I will not present a condition score as a
> validated predictive-maintenance model.

## Interview evidence map

| Recruiter question | Evidence to show | Avoid claiming |
|---|---|---|
| Is it live? | Public read-only Vercel demo and Render readiness endpoint | Paid SLA or guaranteed uptime |
| Is it full stack? | React routes, FastAPI docs, PostgreSQL migrations | Enterprise production adoption |
| Is streaming real? | Redpanda CI smoke path and consumer idempotency | Hosted Kafka or exactly-once delivery |
| Is the AI/ML real? | Statistical signals, feature pipeline, training gate, condition-score disclaimer | Failure prediction accuracy or RUL |
| Is it secure? | RBAC, revocable sessions, rate limits, CodeQL and container scans | Formal penetration test or compliance certification |

## Resume-ready bullets

- Built and deployed a React, FastAPI, and PostgreSQL robotics fleet monitoring
  system with JWT/RBAC, telemetry analytics, operational alerts, and a public
  read-only recruiter demo.
- Implemented idempotent HTTP/Kafka telemetry workflows with Redpanda CI
  integration, retry/DLQ handling, PostgreSQL migrations, and bounded analytics
  APIs for anomaly, trend, and condition signals.
- Added production-container smoke tests, Chromium E2E including 390px mobile
  navigation, CodeQL, dependency audits, container scanning, Prometheus metrics,
  and structured request logging.

These bullets describe implemented scope. Add numeric performance or business
impact only after a reproducible benchmark or real usage measurement exists.
