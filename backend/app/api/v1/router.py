from fastapi import APIRouter, Depends

from app.api.v1.endpoints import papers, profile, projects, research
from app.core.auth import get_current_user

api_router = APIRouter(dependencies=[Depends(get_current_user)])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
