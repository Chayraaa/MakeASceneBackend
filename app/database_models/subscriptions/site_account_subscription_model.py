from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class SiteAccountSubscriptionModel(db.Model):
    __tablename__ = "site_account_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "site_account_id", name="uq_site_account_subscriptions_user_target"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    site_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("site_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    user = relationship("UserModel", back_populates="site_account_subscriptions")
    site_account = relationship("SiteAccountModel", back_populates="subscriptions")
