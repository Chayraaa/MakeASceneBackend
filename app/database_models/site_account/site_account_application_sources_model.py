from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class SiteAccountApplicationSourcesModel(db.Model):
    __tablename__ = "site_account_application_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("site_account_applications.id", ondelete="CASCADE"),
                                                nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)

    application = relationship("SiteAccountApplicationModel", back_populates="sources", lazy="joined")
