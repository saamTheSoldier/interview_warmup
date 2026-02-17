"""
Health checks - for load balancers, Kubernetes, and monitoring.
Challenge: Fast liveness; optional dependency checks for readiness.
"""

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("")
async def health():
    """Liveness: is the process up?"""
    return {"status": "ok", "app": settings.app_name}


@router.get("/ready")
async def ready():
    """Readiness: can accept traffic? (DB/Redis could be checked here.)"""
    return {"status": "ready"}
