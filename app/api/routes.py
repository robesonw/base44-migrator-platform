from fastapi import APIRouter
from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(jobs_router, tags=["jobs"])
