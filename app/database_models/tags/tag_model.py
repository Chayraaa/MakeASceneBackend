from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class TagModel(db.Model):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)

    saved_tags = relationship("SavedTagModel", back_populates="tag", cascade="all, delete-orphan")
    blocked_tags = relationship("BlockedTagModel", back_populates="tag", cascade="all, delete-orphan")
    children = relationship("TagModel", back_populates="parent")
    parent = relationship(
        "TagModel",
        remote_side=[id],
        back_populates="children",
        passive_deletes=True
    )