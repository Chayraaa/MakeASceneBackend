from sqlalchemy import Boolean, Integer, JSON, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class SiteAccountModel(db.Model):
    __tablename__ = "site_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    layout: Mapped[str] = mapped_column(String, nullable=False, default="[]")
    profile_picture: Mapped[str | None] = mapped_column(String, nullable=True)
    banner: Mapped[str] = mapped_column(String, nullable=False, default="")
    colors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    contact: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False, default=list)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    creator = relationship("UserModel", back_populates="site_accounts")
    subscriptions = relationship(
        "SiteAccountSubscriptionModel", back_populates="site_account", cascade="all, delete-orphan"
    )
    owned_events = relationship("EventModel", back_populates="owner")
    collaborating_events = relationship(
        "EventModel", secondary="event_collaborators", back_populates="collaborators"
    )
