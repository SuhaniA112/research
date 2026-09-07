from fastapi import APIRouter

from app.api.deps import CurrentUserDep, ProfileServiceDep
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter()


@router.get("", response_model=ProfileResponse)
async def get_my_profile(
    current_user: CurrentUserDep, service: ProfileServiceDep
) -> ProfileResponse:
    return await service.get_me(current_user)


@router.patch("", response_model=ProfileResponse)
async def update_my_profile(
    payload: ProfileUpdate,
    current_user: CurrentUserDep,
    service: ProfileServiceDep,
) -> ProfileResponse:
    return await service.update_me(current_user, payload)
