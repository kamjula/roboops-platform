# RoboOps

Robotics Fleet Monitoring & Predictive Maintenance Platform.

## Phase 1
React + Vite frontend, FastAPI backend, PostgreSQL via Docker Compose, route placeholders, health endpoint, and starter tests.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:5173 and http://localhost:8000/docs.

## Manual run
Backend: `cd backend`, create/activate a virtual environment, `pip install -r requirements.txt`, then `uvicorn app.main:app --reload`.

Frontend: `cd frontend`, `npm install`, then `npm run dev`.
