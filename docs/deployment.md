# Hosted Demo Deployment

The recruiter demo uses separate services and keeps every credential outside the repository:

- Vercel serves the React single-page application from `frontend/`.
- Render builds the FastAPI production container from `render.yaml`.
- Neon provides a dedicated PostgreSQL 16 project for RoboOps.

Current verified endpoints:

- Frontend: `https://roboops-platform.vercel.app`
- Backend: `https://roboops-api.onrender.com`
- API docs: `https://roboops-api.onrender.com/docs`
- Readiness: `https://roboops-api.onrender.com/health/ready`

Kafka/Redpanda remains an integration-tested local and CI capability. The hosted demo does not claim a managed Kafka deployment.

## Backend environment

Set these values in Render:

- `DATABASE_URL`: the pooled Neon URL, converted to the SQLAlchemy `postgresql+psycopg://` scheme.
- `DATABASE_URL_UNPOOLED`: the direct Neon URL with the same SQLAlchemy scheme. Only Alembic uses it.
- `CORS_ORIGINS`: the exact HTTPS Vercel origin.
- `ROBOOPS_BOOTSTRAP_PASSWORD`: a deployment-only password for the read-only demo account.

Render generates `JWT_SECRET_KEY`. The committed blueprint enables deterministic synthetic seed data and creates `demo@roboops.example` with the `viewer` role. Startup never changes an existing user's password or role.

The production entrypoint runs `alembic upgrade head` against the direct connection, optionally refreshes only the documented deterministic seed fleet, idempotently bootstraps the demo viewer, and then replaces itself with Uvicorn.

## Frontend environment

Configure the Vercel project root as `frontend` and set:

```text
VITE_API_BASE_URL=https://<render-service-host>
```

Redeploy after changing this build-time variable. `frontend/vercel.json` preserves React Router deep links.

## Verification

Do not publish the demo URL until all of these pass:

1. `GET /health/ready` reports `ready` and database `ok`.
2. The demo viewer can log in, load the 12-robot dashboard, open Alerts, and log out.
3. An anonymous dashboard request returns `401`.
4. The viewer cannot call operator/admin write endpoints.
5. The public frontend sends no mixed-content or CORS errors.

## Verification record

On 2026-09-22, the deployed `main` commit `4b0b829` was checked with the
following evidence:

- the Vercel frontend returned HTTP `200`;
- `/health/ready` returned `{"status":"ready","checks":{"database":"ok"}}`;
- a browser-equivalent login preflight from the exact Vercel origin returned
  HTTP `200` with `Access-Control-Allow-Origin` set to that origin; and
- the project owner completed the hosted demo viewer sign-in.

This record does not claim uptime, load-test capacity, hosted Kafka, prediction
accuracy, or business impact. The seeded fleet and telemetry are synthetic.
