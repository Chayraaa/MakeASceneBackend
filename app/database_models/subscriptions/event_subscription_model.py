from sqlalchemy import Boolean, ForeignKey, Integer, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class EventSubscriptionModel(db.Model):
    __tablename__ = "event_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_event_subscriptions_user_target"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    user = relationship("UserModel", back_populates="event_subscriptions")
    event = relationship("EventModel", back_populates="subscriptions")
