from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from app.core.config import settings

MOCK_USER_ID = "mock-user-local-dev"
MOCK_USER_EMAIL = "mock-user@local.dev"


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated identity for the current request.

    In clerk mode this is populated from a verified session token's claims.
    In mock mode it's a fixed sentinel so local dev works without Clerk keys.
    """

    id: str
    email: str | None = None


@dataclass(frozen=True)
class DisplayIdentity:
    """Profile-page display fields, sourced from Clerk rather than stored locally."""

    name: str
    full_name: str
    email: str


async def get_current_user(request: Request) -> CurrentUser:
    if settings.auth_mode == "mock":
        return CurrentUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)

    from clerk_backend_api.security import (
        AuthenticateRequestOptions,
        authenticate_request_async,
    )

    result = await authenticate_request_async(
        request,
        AuthenticateRequestOptions(
            jwt_key=settings.clerk_jwt_key,
            authorized_parties=settings.cors_origins,
        ),
    )
    if not result.is_signed_in or result.payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    user_id = result.payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return CurrentUser(id=user_id, email=result.payload.get("email"))


_clerk_client = None


def _get_clerk_client():
    global _clerk_client
    if _clerk_client is None:
        from clerk_backend_api import Clerk

        _clerk_client = Clerk(bearer_auth=settings.clerk_secret_key)
    return _clerk_client


def _primary_email(user, fallback: str | None) -> str:
    for address in user.email_addresses or []:
        if address.id == user.primary_email_address_id:
            return address.email_address
    return fallback or ""


async def get_display_identity(current_user: CurrentUser) -> DisplayIdentity:
    """Profile name/email for display — never persisted locally, always live from Clerk."""
    if settings.auth_mode == "mock":
        return DisplayIdentity(
            name="Researcher", full_name="Mock User", email=MOCK_USER_EMAIL
        )

    clerk = _get_clerk_client()
    user = await clerk.users.get_async(user_id=current_user.id)

    first_name = (user.first_name or "").strip()
    last_name = (user.last_name or "").strip()
    full_name = f"{first_name} {last_name}".strip()
    email = _primary_email(user, current_user.email)

    return DisplayIdentity(
        name=first_name or full_name or email or "Researcher",
        full_name=full_name or email or "Researcher",
        email=email,
    )
