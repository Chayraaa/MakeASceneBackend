from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


event_tags = Table(
    "event_tags",
    db.metadata,
    Column("event_id", Integer, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

event_collaborators = Table(
    "event_collaborators",
    db.metadata,
    Column("event_id", Integer, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("site_account_id", Integer, ForeignKey("site_accounts.id", ondelete="CASCADE"), primary_key=True),
)


class EventModel(db.Model):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    from_: Mapped[datetime] = mapped_column("from", DateTime(timezone=True), nullable=False)
    till: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    place_id: Mapped[str] = mapped_column(String, ForeignKey("locations.place_id"), nullable=False)
    layout: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("site_accounts.id"), nullable=False)
    access: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    repeating: Mapped[str | None] = mapped_column(String, nullable=True)
    detail_data: Mapped[list[Any]] = mapped_column(JSON, nullable=False)

    owner = relationship("SiteAccountModel", back_populates="owned_events")
    collaborators = relationship(
        "SiteAccountModel", secondary=event_collaborators, back_populates="collaborating_events"
    )
    tags = relationship("TagModel", secondary=event_tags, back_populates="events")
    location = relationship("LocationModel")
