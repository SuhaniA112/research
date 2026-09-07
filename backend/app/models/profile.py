from sqlalchemy import ARRAY, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Profile(Base, TimestampMixin):
    """App-specific preferences for a Clerk-authenticated user.

    Identity (name/email) lives in Clerk, not here — this row only holds
    fields Clerk has no concept of.
    """

    __tablename__ = "profiles"

    # Clerk user id (JWT `sub` claim), e.g. "user_2NNEqL2nrIRdJ...".
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    occupation: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    institution: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    research_areas: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    reading_level: Mapped[str] = mapped_column(
        String(32), nullable=False, default="graduate"
    )
    weekly_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_notifications: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
