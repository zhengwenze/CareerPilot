from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.match_reports import router as match_reports_router
from app.api.routes.mock_interviews import router as mock_interviews_router
from app.api.routes.profile import router as profile_router
from app.api.routes.resume_optimization import router as resume_optimization_router
from app.api.routes.resumes import router as resumes_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(profile_router)
api_router.include_router(resumes_router)
api_router.include_router(resume_optimization_router)
api_router.include_router(jobs_router)
api_router.include_router(match_reports_router)
api_router.include_router(mock_interviews_router)
