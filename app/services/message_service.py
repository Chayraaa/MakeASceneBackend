from app.domain_models.messages.message import Message
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
    def send_message(self, notify_message: NotifyMessage, user: User): ...

    # Pagenate this in the repo
    def get_messages(self, user: User) -> list[Message] | None:
        return self.message_repo.get_messages_by_user_id(user.id)

    def delete_message(self, message_id: int) -> bool:
        message = self.message_repo.get_message_by_id(message_id)
        if message is None:
            return False
        return self.message_repo.delete_message(message)

    def mark_message_as_read(self, message_id: int) -> bool:
        message = self.message_repo.get_message_by_id(message_id)
        if message is None:
            return False
        message.read = True
        return self.message_repo.update_message(message)