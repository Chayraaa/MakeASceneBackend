from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class SiteAccountApplicationModel(db.Model):
    __tablename__ = "site_account_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requestor_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    artist_name: Mapped[str] = mapped_column(nullable=False)
    account_name: Mapped[str] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(nullable=False)

    requestor = relationship("UserModel", back_populates="site_account_applications")
    sources = relationship("SiteAccountApplicationSourcesModel", back_populates="application", cascade="all, delete-orphan")
    contacts = relationship("SiteAccountApplicationContactModel", back_populates="application", cascade="all, delete-orphan")
