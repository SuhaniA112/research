"""Shared construction helpers for the eval scripts.

These scripts run outside the FastAPI request lifecycle, so they build repos/services
directly against a session rather than going through app.api.deps's Depends chains.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.services.ask_service import AskService
from app.services.embeddings.voyage_client import VoyageEmbeddingClient
from app.services.generation.openrouter_client import OpenRouterClient


def build_voyage_client() -> VoyageEmbeddingClient:
    return VoyageEmbeddingClient(
        api_key=settings.voyage_api_key, model=settings.voyage_embedding_model
    )


def build_openrouter_client() -> OpenRouterClient:
    return OpenRouterClient(
        api_key=settings.openrouter_api_key, model=settings.openrouter_model
    )


def build_ask_service(session: AsyncSession) -> AskService:
    return AskService(
        ProjectRepository(session),
        ChunkRepository(session),
        build_voyage_client(),
        build_openrouter_client(),
        max_distance=settings.retrieval_max_distance,
        top_k=settings.retrieval_top_k,
    )


def build_paper_repo(session: AsyncSession) -> PaperRepository:
    return PaperRepository(session)


def build_chunk_repo(session: AsyncSession) -> ChunkRepository:
    return ChunkRepository(session)


def build_project_paper_repo(session: AsyncSession) -> ProjectPaperRepository:
    return ProjectPaperRepository(session)
