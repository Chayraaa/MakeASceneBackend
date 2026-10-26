import logging

from sqlalchemy.exc import SQLAlchemyError

from app.database_models.subscriptions.site_account_subscription_model import SiteAccountSubscriptionModel
from app.domain_models.subscriptions.site_account_subscription import SiteAccountSubscription

logger = logging.getLogger(__name__)


class SqlSiteAccountSubscriptionRepo:
    def __init__(self, session):
        self.session = session

    def create(self, subscription: SiteAccountSubscription) -> bool:
        try:
            model = SiteAccountSubscriptionModel(
                user_id=subscription.user_id,
                site_account_id=subscription.site_account_id,
                notifications_enabled=subscription.notifications_enabled,
            )
            self.session.add(model)
            self.session.commit()
            subscription.id = model.id
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to create site_account subscription")
            return False

    def get_by_id(self, subscription_id: int) -> SiteAccountSubscription | None:
        try:
            model = self.session.get(SiteAccountSubscriptionModel, subscription_id)
            return self._to_domain(model) if model is not None else None
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to get site_account subscription")
            return None

    def get_by_user_id(self, user_id: int, page: int = 1, page_size: int = 20) -> list[SiteAccountSubscription] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        try:
            models = (self.session.query(SiteAccountSubscriptionModel)
                      .filter_by(user_id=user_id)
                      .order_by(SiteAccountSubscriptionModel.id.asc())
                      .offset((page - 1) * page_size)
                      .limit(page_size).all())
            return [self._to_domain(model) for model in models]
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to list site_account subscriptions by user_id")
            return None

    def get_by_site_account_id(self, site_account_id: int, page: int = 1, page_size: int = 20) -> list[SiteAccountSubscription] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        try:
            models = (self.session.query(SiteAccountSubscriptionModel)
                      .filter_by(site_account_id=site_account_id)
                      .order_by(SiteAccountSubscriptionModel.id.asc())
                      .offset((page - 1) * page_size)
                      .limit(page_size).all())
            return [self._to_domain(model) for model in models]
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to list site_account subscriptions by site_account_id")
            return None

    def get_by_user_and_site_account_id(self, user_id: int, site_account_id: int) -> SiteAccountSubscription | None:
        try:
            model = self.session.query(SiteAccountSubscriptionModel).filter_by(
                user_id=user_id, site_account_id=site_account_id
            ).first()
            return self._to_domain(model) if model is not None else None
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to get user site_account subscription")
            return None

    def update(self, subscription: SiteAccountSubscription) -> bool:
        try:
            model = self.session.get(SiteAccountSubscriptionModel, subscription.id)
            if model is None:
                return False
            model.user_id = subscription.user_id
            model.site_account_id = subscription.site_account_id
            model.notifications_enabled = subscription.notifications_enabled
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to update site_account subscription")
            return False

    def delete(self, subscription: SiteAccountSubscription) -> bool:
        try:
            model = self.session.get(SiteAccountSubscriptionModel, subscription.id)
            if model is None:
                return False
            self.session.delete(model)
            self.session.commit()
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to delete site_account subscription")
            return False

    @staticmethod
    def _to_domain(model: SiteAccountSubscriptionModel) -> SiteAccountSubscription:
        return SiteAccountSubscription(
            id=model.id,
            user_id=model.user_id,
            site_account_id=model.site_account_id,
            notifications_enabled=model.notifications_enabled,
        )
