from fastapi import APIRouter

from app.api.v1.endpoints import papers, projects, research, users

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(research.router, prefix="/research", tags=["research"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
