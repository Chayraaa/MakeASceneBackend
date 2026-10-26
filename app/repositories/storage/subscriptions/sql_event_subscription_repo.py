import logging

from sqlalchemy.exc import SQLAlchemyError

from app.database_models.subscriptions.event_subscription_model import EventSubscriptionModel
from app.domain_models.subscriptions.event_subscription import EventSubscription

logger = logging.getLogger(__name__)


class SqlEventSubscriptionRepo:
    def __init__(self, session):
        self.session = session

    def create(self, subscription: EventSubscription) -> bool:
        try:
            model = EventSubscriptionModel(
                user_id=subscription.user_id,
                event_id=subscription.event_id,
                notifications_enabled=subscription.notifications_enabled,
            )
            self.session.add(model)
            self.session.commit()
            subscription.id = model.id
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to create event subscription")
            return False

    def get_by_id(self, subscription_id: int) -> EventSubscription | None:
        try:
            model = self.session.get(EventSubscriptionModel, subscription_id)
            return self._to_domain(model) if model is not None else None
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to get event subscription")
            return None

    def get_by_user_id(self, user_id: int, page: int = 1, page_size: int = 20) -> list[EventSubscription] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        try:
            models = (self.session.query(EventSubscriptionModel)
                      .filter_by(user_id=user_id)
                      .order_by(EventSubscriptionModel.id.asc())
                      .offset((page - 1) * page_size)
                      .limit(page_size).all())
            return [self._to_domain(model) for model in models]
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to list event subscriptions by user_id")
            return None

    def get_by_event_id(self, event_id: int, page: int = 1, page_size: int = 20) -> list[EventSubscription] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        try:
            models = (self.session.query(EventSubscriptionModel)
                      .filter_by(event_id=event_id)
                      .order_by(EventSubscriptionModel.id.asc())
                      .offset((page - 1) * page_size)
                      .limit(page_size).all())
            return [self._to_domain(model) for model in models]
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to list event subscriptions by event_id")
            return None

    def get_by_user_and_event_id(self, user_id: int, event_id: int) -> EventSubscription | None:
        try:
            model = self.session.query(EventSubscriptionModel).filter_by(
                user_id=user_id, event_id=event_id
            ).first()
            return self._to_domain(model) if model is not None else None
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to get user event subscription")
            return None

    def update(self, subscription: EventSubscription) -> bool:
        try:
            model = self.session.get(EventSubscriptionModel, subscription.id)
            if model is None:
                return False
            model.user_id = subscription.user_id
            model.event_id = subscription.event_id
            model.notifications_enabled = subscription.notifications_enabled
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to update event subscription")
            return False

    def delete(self, subscription: EventSubscription) -> bool:
        try:
            model = self.session.get(EventSubscriptionModel, subscription.id)
            if model is None:
                return False
            self.session.delete(model)
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to delete event subscription")
            return False

    @staticmethod
    def _to_domain(model: EventSubscriptionModel) -> EventSubscription:
        return EventSubscription(
            id=model.id,
            user_id=model.user_id,
            event_id=model.event_id,
            notifications_enabled=model.notifications_enabled,
        )
