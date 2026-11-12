from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.router import api_router
from backend.core.config import settings

app = FastAPI(
    title="UAV-QAOA-SAR API",
    description="Quantum-Optimized UAV Waypoint Selection for Rapid Search-and-Rescue Localization",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_root():
    return {"status": "ok", "service": "uav-qaoa-sar-backend"}


@app.get("/")
def root():
    return {
        "message": "UAV-QAOA-SAR Backend Active",
        "docs_url": "/docs",
        "health_check": "/health",
    }
