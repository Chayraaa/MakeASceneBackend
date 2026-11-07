import logging

from sqlalchemy.exc import SQLAlchemyError

from app.database_models.subscriptions.location_subscription_model import LocationSubscriptionModel
from app.domain_models.subscriptions.location_subscription import LocationSubscription

logger = logging.getLogger(__name__)


class SqlLocationSubscriptionRepo:
    def __init__(self, session):
        self.session = session

    def create(self, subscription: LocationSubscription) -> bool:
        try:
            model = LocationSubscriptionModel(
                user_id=subscription.user_id,
                location_id=subscription.location_id,
            )
            self.session.add(model)
            self.session.commit()
            subscription.id = model.id
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to create location subscription")
            return False

    def get_by_id(self, subscription_id: int) -> LocationSubscription | None:
        try:
            model = self.session.get(LocationSubscriptionModel, subscription_id)
            return self._to_domain(model) if model is not None else None
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to get location subscription")
            return None

    def get_by_user_id(self, user_id: int, page: int = 1, page_size: int = 20) -> list[LocationSubscription] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        try:
            models = (self.session.query(LocationSubscriptionModel)
                      .filter_by(user_id=user_id)
                      .order_by(LocationSubscriptionModel.id.asc())
                      .offset((page - 1) * page_size)
                      .limit(page_size).all())
            return [self._to_domain(model) for model in models]
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to list location subscriptions by user_id")
            return None

    def get_by_location_id(self, location_id: int, page: int = 1, page_size: int = 20) -> list[LocationSubscription] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        try:
            models = (self.session.query(LocationSubscriptionModel)
                      .filter_by(location_id=location_id)
                      .order_by(LocationSubscriptionModel.id.asc())
                      .offset((page - 1) * page_size)
                      .limit(page_size).all())
            return [self._to_domain(model) for model in models]
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to list location subscriptions by location_id")
            return None

    def get_by_user_and_location_id(self, user_id: int, location_id: int) -> LocationSubscription | None:
        try:
            model = self.session.query(LocationSubscriptionModel).filter_by(
                user_id=user_id, location_id=location_id
            ).first()
            return self._to_domain(model) if model is not None else None
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to get user location subscription")
            return None

    def update(self, subscription: LocationSubscription) -> bool:
        try:
            model = self.session.get(LocationSubscriptionModel, subscription.id)
            if model is None:
                return False
            model.user_id = subscription.user_id
            model.location_id = subscription.location_id
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to update location subscription")
            return False

    def delete(self, subscription: LocationSubscription) -> bool:
        try:
            model = self.session.get(LocationSubscriptionModel, subscription.id)
            if model is None:
                return False
            self.session.delete(model)
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to delete location subscription")
            return False

    @staticmethod
    def _to_domain(model: LocationSubscriptionModel) -> LocationSubscription:
        return LocationSubscription(
            id=model.id,
            user_id=model.user_id,
            location_id=model.location_id,
        )
