from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.current_user import USER_ID_HEADER
from app.core.config import settings
from app.core.database import get_async_session
from app.models.user import User
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.paper_repo import PaperRepository
from app.repositories.project_paper_repo import ProjectPaperRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.search_execution_repo import SearchExecutionRepository
from app.repositories.search_topic_paper_repo import SearchTopicPaperRepository
from app.repositories.search_topic_repo import SearchTopicRepository
from app.repositories.profile_repo import ProfileRepository
from app.repositories.user_repo import UserRepository
from app.services.ask_service import AskService
from app.services.discovery_search_service import DiscoverySearchService
from app.services.embeddings.voyage_client import VoyageEmbeddingClient
from app.services.generation.openrouter_client import OpenRouterClient
from app.services.ingestion_service import IngestionService
from app.services.indexing.paper_indexer import PaperIndexer
from app.services.profile_service import ProfileService
from app.services.project_service import ProjectService
from app.services.research_service import ResearchService
from app.services.summarization.paper_summarizer import PaperSummarizer
from app.services.user_service import UserService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    session: DbSession,
    x_user_id: Annotated[str | None, Header(alias=USER_ID_HEADER)] = None,
) -> User:
    """Resolve the temporary current user from ``X-User-ID``.

    Temporary until real authentication exists. Validates UUID format and that
    the user row exists and is active. Do not parse this header in endpoints.
    """
    if x_user_id is None or not str(x_user_id).strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                f"Missing {USER_ID_HEADER} header. "
                "Temporary user context is required until real auth exists."
            ),
        )

    try:
        user_id = UUID(str(x_user_id).strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{USER_ID_HEADER} must be a valid UUID",
        ) from exc

    user_repo = UserRepository(session)
    user = await user_repo.get_active_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User {user_id} not found or inactive",
        )
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_user_repository(session: DbSession) -> UserRepository:
    return UserRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_service(user_repo: UserRepoDep) -> UserService:
    return UserService(user_repo)


def get_research_service() -> ResearchService:
    return ResearchService()


ResearchServiceDep = Annotated[ResearchService, Depends(get_research_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_profile_repository(session: DbSession) -> ProfileRepository:
    return ProfileRepository(session)


ProfileRepoDep = Annotated[ProfileRepository, Depends(get_profile_repository)]


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


def get_project_service(
    project_repo: ProjectRepoDep,
    project_paper_repo: ProjectPaperRepoDep,
) -> ProjectService:
    return ProjectService(project_repo, project_paper_repo)


def get_profile_service(
    profile_repo: ProfileRepoDep,
    project_repo: ProjectRepoDep,
    project_paper_repo: ProjectPaperRepoDep,
) -> ProfileService:
    return ProfileService(profile_repo, project_repo, project_paper_repo)


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


def get_paper_indexer() -> PaperIndexer:
    return PaperIndexer()


PaperIndexerDep = Annotated[PaperIndexer, Depends(get_paper_indexer)]


def get_paper_summarizer(openrouter_client: OpenRouterClientDep) -> PaperSummarizer:
    return PaperSummarizer(openrouter_client)


PaperSummarizerDep = Annotated[PaperSummarizer, Depends(get_paper_summarizer)]


def get_ingestion_service(
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
    project_paper_repo: ProjectPaperRepoDep,
    project_repo: ProjectRepoDep,
    voyage_client: VoyageClientDep,
    paper_indexer: PaperIndexerDep,
    paper_summarizer: PaperSummarizerDep,
) -> IngestionService:
    return IngestionService(
        paper_repo,
        chunk_repo,
        project_paper_repo,
        project_repo,
        voyage_client,
        paper_indexer,
        paper_summarizer,
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
        ann_overfetch=settings.retrieval_ann_overfetch,
    )


def get_discovery_search_service(
    paper_repo: PaperRepoDep,
    chunk_repo: ChunkRepoDep,
    search_topic_repo: SearchTopicRepoDep,
    search_execution_repo: SearchExecutionRepoDep,
    search_topic_paper_repo: SearchTopicPaperRepoDep,
    project_repo: ProjectRepoDep,
    profile_repo: ProfileRepoDep,
    voyage_client: VoyageClientDep,
) -> DiscoverySearchService:
    return DiscoverySearchService(
        paper_repo=paper_repo,
        chunk_repo=chunk_repo,
        search_topic_repo=search_topic_repo,
        search_execution_repo=search_execution_repo,
        search_topic_paper_repo=search_topic_paper_repo,
        project_repo=project_repo,
        profile_repo=profile_repo,
        voyage_client=voyage_client,
        settings=settings,
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
AskServiceDep = Annotated[AskService, Depends(get_ask_service)]
DiscoverySearchServiceDep = Annotated[
    DiscoverySearchService, Depends(get_discovery_search_service)
]
