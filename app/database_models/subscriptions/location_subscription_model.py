from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class LocationSubscriptionModel(db.Model):
    __tablename__ = "location_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "location_id", name="uq_location_subscriptions_user_target"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    user = relationship("UserModel", back_populates="location_subscriptions")
    location = relationship("LocationModel", back_populates="subscriptions")
