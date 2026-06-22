from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class SiteAccountModel(db.Model):
    __tablename__ = "site_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    layout: Mapped[str] = mapped_column(String, nullable=False, default="[]")

    creator = relationship("UserModel", back_populates="site_accounts")
