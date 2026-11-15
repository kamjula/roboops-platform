# RoboOps — 90-second demo tour

A short walkthrough of what is already implemented in the repository and the
hosted read-only demo. It adds no performance, accuracy, uptime, or
business-impact claims beyond what has been measured.

## Open the demo

1. Go to <https://roboops-platform.vercel.app> and select **Explore read-only
   demo**. The Render free instance can need a short cold start after
   inactivity.
2. Keep the [API documentation](https://roboops-api.onrender.com/docs) and the
   [GitHub Actions runs](https://github.com/kamjula/roboops-platform/actions)
   open alongside it.

## 0–20 s · Product and data boundary

Open the **Dashboard**. The hosted demo runs a bounded synthetic telemetry
stream for 12 fictional robots, so the complete workflow is visible without
real customer data or real-world prediction-accuracy claims. Recent alerts show
separate trigger and recorded timestamps.

## 20–45 s · Telemetry and analytics

Open **Telemetry**, then **Analytics**.

- Readings enter through an idempotent FastAPI ingestion contract and are
  stored in PostgreSQL. A repeated telemetry event is handled through
  application-level idempotency instead of creating a duplicate reading.
- The analytics workspace shows threshold events, statistical baseline
  signals, bounded trend series, and fleet condition scores across 24-, 72-,
  and 168-hour windows, using bounded API queries rather than loading unbounded
  history into the browser.
- Condition scores are labeled as anomaly signals, not failure probability or
  remaining useful life, because the project has no labeled failure outcomes.

## 45–70 s · Operations and access control

Open **Alerts**, **Tasks**, and **Maintenance**.

- Alerts are persisted records with an authenticated lifecycle.
- Tasks is a review queue derived from open alerts and maintenance schedules;
  there is no separate task-management backend.
- The public demo receives a short-lived viewer session, and server-side RBAC
  blocks writes.
- Logout revokes the database-backed JWT session; CI verifies that the old
  token is rejected afterward.
- Login and telemetry-write endpoints return `429` with rate-limit headers. The
  limiter is process-local, as documented in the README.

## 70–90 s · Delivery evidence

Open the [GitHub Actions](https://github.com/kamjula/roboops-platform/actions)
page or the README badges. CI runs backend and PostgreSQL tests, frontend tests
and build, a real Redpanda-to-PostgreSQL smoke path, production-container smoke
tests, Chromium E2E, CodeQL, dependency audits, and container scans. The
frontend is hosted on Vercel, the API on Render, and PostgreSQL on Neon.

**Known limitation:** the next engineering step is labeled failure data and
time-aware model evaluation. Until that exists, the condition score is not
presented as a validated predictive-maintenance model.

## Evidence map

| Question | Where to look | Not claimed |
|---|---|---|
| Is it live? | Public read-only Vercel demo and Render readiness endpoint | Paid SLA or guaranteed uptime |
| Is it full stack? | React routes, FastAPI docs, PostgreSQL migrations | Enterprise production adoption |
| Is streaming real? | Redpanda CI smoke path and consumer idempotency | Hosted Kafka or exactly-once delivery |
| Is the ML real? | Statistical signals, feature pipeline, training gate, condition-score disclaimer | Failure-prediction accuracy or remaining useful life |
| Is it secure? | RBAC, revocable sessions, rate limits, CodeQL and container scans | Formal penetration test or compliance certification |
