import asyncio
import logging
import time
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.observability import ObservabilityMiddleware, REQUEST_ID_HEADER
from app.core.observability import router as observability_router
from app.core.rate_limit import FixedWindowRateLimiter
from app.services.demo_stream_service import refresh_demo_readings
from app.routers.alerts import router as alerts_router
from app.routers.auth import router as auth_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.robot_models import router as robot_models_router
from app.routers.robots import router as robots_router
from app.routers.sites import router as sites_router
from app.routers.telemetry import router as telemetry_router

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if settings.roboops_synthetic_stream_enabled:
        try:
            await asyncio.to_thread(refresh_demo_readings, startup=True)
        except Exception:
            logger.exception("Synthetic demo telemetry initialization failed; will retry")

        async def refresh_loop():
            while True:
                await asyncio.sleep(max(1, 300 - time.time() % 300 + 0.1))
                try:
                    await asyncio.to_thread(refresh_demo_readings)
                except Exception:
                    logger.exception("Synthetic demo telemetry refresh failed; will retry")

        task = asyncio.create_task(refresh_loop())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    title="RoboOps API",
    description="Robotics Fleet Monitoring & Predictive Maintenance Platform",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.rate_limiter = FixedWindowRateLimiter(max_keys=settings.rate_limit_max_keys)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)
app.add_middleware(ObservabilityMiddleware)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(observability_router)
app.include_router(sites_router)
app.include_router(robot_models_router)
app.include_router(robots_router)
app.include_router(dashboard_router)
app.include_router(telemetry_router)
app.include_router(alerts_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "RoboOps API is running"}
