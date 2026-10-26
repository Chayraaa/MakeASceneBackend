import logging

from sqlalchemy.exc import SQLAlchemyError

from app.database_models.messages.message_model import MessageModel
from app.domain_models.messages.message import Message

logger = logging.getLogger(__name__)


class SqlMessageRepo:
    def __init__(self, session):
        self.session = session

    def create_message(self, message: Message) -> bool:
        try:
            model = MessageModel(
                user_id=message.user_id,
                title=message.title,
                message=message.message,
                sent_at=message.sent_at,
                read=message.read,
            )
            self.session.add(model)
            self.session.commit()
            logger.info("Created message %s", message.id)
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to create message for user %s", message.user_id)
            return False

    def get_message_by_id(self, message_id: int) -> Message | None:
        try:
            model = self.session.get(MessageModel, message_id)
            if model is None:
                logger.debug("Message %s not found", message_id)
                return None
            return self._to_domain(model)
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to get message %s", message_id)
            return None

    def get_messages_by_user_id(self, user_id: int, page: int, page_size: int) -> list[Message] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        try:
            models = (self.session.query(MessageModel)
                      .filter_by(user_id=user_id)
                      .order_by(MessageModel.sent_at.desc())
                      .offset((page - 1) * page_size)
                      .limit(page_size).all())
            return [self._to_domain(model) for model in models]
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to get messages for user %s", user_id)
            return None

    def update_message(self, message: Message) -> bool:
        try:
            model = self.session.get(MessageModel, message.id)
            if model is None:
                logger.warning("Cannot update message %s: not found", message.id)
                return False
            model.user_id = message.user_id
            model.title = message.title
            model.message = message.message
            model.sent_at = message.sent_at
            model.read = message.read
            self.session.commit()
            logger.info("Updated message %s", message.id)
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to update message %s", message.id)
            return False

    def delete_message(self, message: Message) -> bool:
        try:
            model = self.session.get(MessageModel, message.id)
            if model is None:
                logger.warning("Cannot delete message %s: not found", message.id)
                return False
            self.session.delete(model)
            self.session.commit()
            logger.info("Deleted message %s", message.id)
            return True
        except SQLAlchemyError:
            self.session.rollback()
            logger.exception("Failed to delete message %s", message.id)
            return False

    @staticmethod
    def _to_domain(model: MessageModel) -> Message:
        return Message(
            id=model.id,
            user_id=model.user_id,
            title=model.title,
            message=model.message,
            sent_at=model.sent_at,
            read=model.read,
        )
