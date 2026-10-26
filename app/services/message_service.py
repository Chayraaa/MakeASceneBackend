from app.domain_models.messages.message import Message
from app.email_templates import render_email_template
from app.domain_models.messages.notify_message import NotifyMessage
from app.domain_models.user import User
from app.repositories.interfaces.external.email_protocol import EmailProtocol
from app.repositories.interfaces.storage.messages.message_storage_protocol import MessageStorageProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol


class MessageService:
    def __init__(self, message_repo: MessageStorageProtocol, email_repo: EmailProtocol, user_repo: UserRepoProtocol):
        self.message_repo = message_repo
        self.email_repo = email_repo
        self.user_repo = user_repo

    # Sends a message to the database and via email based on the user flags
    def send_message(self, notify_message: NotifyMessage, user: User) -> bool:
        if not notify_message.title or not notify_message.body:
            return False
        user = self.user_repo.get_user(user.id)
        if user is None:
            return False
        if not self.message_repo.create_message(Message(user_id=user.id, title=notify_message.title, message=notify_message.body)):
            return False
        if user.email_preference:
            email_content = render_email_template(
                "user_message.html", title=notify_message.title, message=notify_message.body,
                unsubscribe_url="#",  # Placeholder until unsubscribe is implemented.
            )
            self.email_repo.send_email(subject=notify_message.title, body=email_content, recipient=user.email)
        return True

    def get_messages(self, user: User, page: int = 1, page_size: int = 20) -> list[Message] | None:
        if page < 1 or page_size < 1:
            return None
        return self.message_repo.get_messages_by_user_id(user.id, page, page_size)

    def delete_message(self, message_id: int, user: User) -> bool | None:
        """Return None for missing/unowned messages, otherwise the write result."""
        message = self.message_repo.get_message_by_id(message_id)
        if message is None:
            return None
        if message.user_id != user.id:
            return None
        return self.message_repo.delete_message(message)

    def mark_message_as_read(self, message_id: int, user: User, read: bool) -> bool | None:
        """Return None for missing/unowned messages, otherwise the write result."""
        message = self.message_repo.get_message_by_id(message_id)
        if message is None:
            return None
        if message.user_id != user.id:
            return None
        message.read = read
        return self.message_repo.update_message(message)
