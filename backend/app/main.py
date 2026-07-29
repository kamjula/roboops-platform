from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.routers.health import router as health_router
settings=get_settings()
app=FastAPI(title="RoboOps API",description="Robotics Fleet Monitoring & Predictive Maintenance Platform",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(health_router)
@app.get("/")
def root():
    return {"message":"RoboOps API is running"}
