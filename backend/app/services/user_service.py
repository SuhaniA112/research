import hashlib
from uuid import UUID

from fastapi import HTTPException, status

from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    @staticmethod
    def _hash_password(password: str) -> str:
        # Placeholder — replace with bcrypt/argon2 in production
        return hashlib.sha256(password.encode()).hexdigest()

    async def get_user(self, user_id: UUID) -> UserResponse:
        user = await self.user_repo.get_active_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return UserResponse.model_validate(user)

    async def list_users(self, *, skip: int = 0, limit: int = 100) -> list[UserResponse]:
        users = await self.user_repo.list_active(skip=skip, limit=limit)
        return [UserResponse.model_validate(user) for user in users]

    async def create_user(self, payload: UserCreate) -> UserResponse:
        existing = await self.user_repo.get_by_email(payload.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=self._hash_password(payload.password),
            is_active=True,
        )
        created = await self.user_repo.create(user)
        return UserResponse.model_validate(created)

    async def update_user(self, user_id: UUID, payload: UserUpdate) -> UserResponse:
        user = await self.user_repo.get_active_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        updated = await self.user_repo.update(user)
        return UserResponse.model_validate(updated)

    async def delete_user(self, user_id: UUID) -> None:
        user = await self.user_repo.get_active_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        await self.user_repo.delete(user)
