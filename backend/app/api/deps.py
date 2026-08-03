from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.search_execution_repo import SearchExecutionRepository
from app.repositories.search_topic_paper_repo import SearchTopicPaperRepository
from app.repositories.search_topic_repo import SearchTopicRepository
from app.repositories.user_repo import UserRepository
from app.services.ask_service import AskService
from app.services.discovery_search_service import DiscoverySearchService
from app.services.embeddings.voyage_client import VoyageEmbeddingClient
from app.services.generation.openrouter_client import OpenRouterClient
from app.services.ingestion_service import IngestionService
from app.services.indexing.paper_indexer import PaperIndexer
from app.services.project_service import ProjectService
from app.services.research_service import ResearchService
from app.services.user_service import UserService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_user_repository(session: DbSession) -> UserRepository:
    return UserRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_service(user_repo: UserRepoDep) -> UserService:
    return UserService(user_repo)


def get_research_service() -> ResearchService:
    return ResearchService()


ResearchServiceDep = Annotated[ResearchService, Depends(get_research_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_project_repository(session: DbSession) -> ProjectRepository:
    return ProjectRepository(session)


def get_paper_repository(session: DbSession) -> PaperRepository:
    return PaperRepository(session)


def get_chunk_repository(session: DbSession) -> ChunkRepository:
    return ChunkRepository(session)


def get_project_paper_repository(session: DbSession) -> ProjectPaperRepository:
    return ProjectPaperRepository(session)


def get_search_topic_repository(session: DbSession) -> SearchTopicRepository:
    return SearchTopicRepository(session)


def get_search_execution_repository(session: DbSession) -> SearchExecutionRepository:
    return SearchExecutionRepository(session)


def get_search_topic_paper_repository(
    session: DbSession,
) -> SearchTopicPaperRepository:
    return SearchTopicPaperRepository(session)


ProjectRepoDep = Annotated[ProjectRepository, Depends(get_project_repository)]
PaperRepoDep = Annotated[PaperRepository, Depends(get_paper_repository)]
ChunkRepoDep = Annotated[ChunkRepository, Depends(get_chunk_repository)]
ProjectPaperRepoDep = Annotated[
    ProjectPaperRepository, Depends(get_project_paper_repository)
]
SearchTopicRepoDep = Annotated[
    SearchTopicRepository, Depends(get_search_topic_repository)
]
SearchExecutionRepoDep = Annotated[
    SearchExecutionRepository, Depends(get_search_execution_repository)
]
SearchTopicPaperRepoDep = Annotated[
    SearchTopicPaperRepository, Depends(get_search_topic_paper_repository)
]


def get_voyage_client() -> VoyageEmbeddingClient:
    return VoyageEmbeddingClient(
        api_key=settings.voyage_api_key, model=settings.voyage_embedding_model
    )


def get_openrouter_client() -> OpenRouterClient:
    return OpenRouterClient(
        api_key=settings.openrouter_api_key, model=settings.openrouter_model
    )


VoyageClientDep = Annotated[VoyageEmbeddingClient, Depends(get_voyage_client)]
OpenRouterClientDep = Annotated[OpenRouterClient, Depends(get_openrouter_client)]


def get_project_service(project_repo: ProjectRepoDep) -> ProjectService:
    return ProjectService(project_repo)


def get_paper_indexer() -> PaperIndexer:
    return PaperIndexer()


PaperIndexerDep = Annotated[PaperIndexer, Depends(get_paper_indexer)]


def get_ingestion_service(
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
    project_paper_repo: ProjectPaperRepoDep,
    project_repo: ProjectRepoDep,
    voyage_client: VoyageClientDep,
    paper_indexer: PaperIndexerDep,
) -> IngestionService:
    return IngestionService(
        paper_repo,
        chunk_repo,
        project_paper_repo,
        project_repo,
        voyage_client,
        paper_indexer,
    )


def get_ask_service(
    project_repo: ProjectRepoDep,
    chunk_repo: ChunkRepoDep,
    voyage_client: VoyageClientDep,
    openrouter_client: OpenRouterClientDep,
) -> AskService:
    return AskService(
        project_repo,
        chunk_repo,
        voyage_client,
        openrouter_client,
        max_distance=settings.retrieval_max_distance,
        top_k=settings.retrieval_top_k,
    )


def get_discovery_search_service(
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
    search_topic_repo: SearchTopicRepoDep,
    search_execution_repo: SearchExecutionRepoDep,
    search_topic_paper_repo: SearchTopicPaperRepoDep,
    voyage_client: VoyageClientDep,
) -> DiscoverySearchService:
    return DiscoverySearchService(
        paper_repo=paper_repo,
        chunk_repo=chunk_repo,
        search_topic_repo=search_topic_repo,
        search_execution_repo=search_execution_repo,
        search_topic_paper_repo=search_topic_paper_repo,
        voyage_client=voyage_client,
        settings=settings,
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
AskServiceDep = Annotated[AskService, Depends(get_ask_service)]
DiscoverySearchServiceDep = Annotated[
    DiscoverySearchService, Depends(get_discovery_search_service)
]
