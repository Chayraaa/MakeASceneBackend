from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class TagModel(db.Model):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)

    saved_tags = relationship("SavedTagModel", back_populates="tag", cascade="all, delete-orphan")
    blocked_tags = relationship("BlockedTagModel", back_populates="tag", cascade="all, delete-orphan")
