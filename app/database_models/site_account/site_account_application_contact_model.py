from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class SiteAccountApplicationContactModel(db.Model):
    __tablename__ = "site_account_application_contacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("site_account_applications.id", ondelete="CASCADE"),
                                                nullable=False)
    contact: Mapped[str] = mapped_column(nullable=False)

    application = relationship("SiteAccountApplicationModel", back_populates="contacts", lazy="joined")
