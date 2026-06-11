from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repositories.user_repo import UserRepository
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


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
