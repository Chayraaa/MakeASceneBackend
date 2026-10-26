from dataclasses import dataclass


@dataclass
class NotifyMessage:
    title: str
    body: str
    email_content: str

    def to_dict(self):
        return {
            "title": self.title,
            "body": self.body,
        }