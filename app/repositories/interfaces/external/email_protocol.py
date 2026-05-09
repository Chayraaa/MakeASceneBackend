from typing import Protocol


class EmailProtocol(Protocol):
    def send_email(self, subject: str, body: str, recipient: str): ...
