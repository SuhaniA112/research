from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.deps import ProfileServiceDep, UserServiceDep
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(service: ProfileServiceDep) -> ProfileResponse:
    """Shared app profile until real auth exists."""
    return await service.get_me()


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    payload: ProfileUpdate,
    service: ProfileServiceDep,
) -> ProfileResponse:
    return await service.update_me(payload)


@router.get("", response_model=list[UserResponse])
async def list_users(
    service: UserServiceDep,
    skip: int = 0,
    limit: int = 100,
) -> list[UserResponse]:
    return await service.list_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: UUID, service: UserServiceDep) -> UserResponse:
    return await service.get_user(user_id)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, service: UserServiceDep) -> UserResponse:
    return await service.create_user(payload)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: UserServiceDep,
) -> UserResponse:
    return await service.update_user(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, service: UserServiceDep) -> Response:
    await service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
