from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


# Defines a user in the database. Will automatically create tables and interactions in flask.
# Basically an easy way to avoid SQL lul.
# Take this as a template if more needs to be created. See sqlalchemy docs for capabilities.
class UserModel(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    password: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    oauth_method: Mapped[str] = mapped_column(nullable=False, default="local")
    confirmed: Mapped[bool] = mapped_column(nullable=False, default=False)
    mature: Mapped[bool] = mapped_column(nullable=False, default=True)
    email_preference: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Auth
    refresh_tokens = relationship(
        "RefreshTokenModel", back_populates="user", cascade="all, delete-orphan"
    )
    confirm_tokens = relationship(
        "ConfirmTokenModel", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens = relationship(
        "PasswordResetTokenModel", back_populates="user", cascade="all, delete-orphan"
    )
    # Tags
    saved_tags = relationship(
        "SavedTagModel", back_populates="user", cascade="all, delete-orphan"
    )
    blocked_tags = relationship(
        "BlockedTagModel", back_populates="user", cascade="all, delete-orphan"
    )
