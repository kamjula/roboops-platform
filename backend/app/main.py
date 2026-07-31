from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.routers.health import router as health_router
from app.routers.sites import router as sites_router
from app.routers.robot_models import router as robot_models_router
from app.routers.robots import router as robots_router
settings=get_settings()
app=FastAPI(title="RoboOps API",description="Robotics Fleet Monitoring & Predictive Maintenance Platform",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(health_router)
app.include_router(sites_router)
app.include_router(robot_models_router)
app.include_router(robots_router)
@app.get("/")
def root():
    return {"message":"RoboOps API is running"}
