import os

import resend

resend_api_key = os.environ.get("RESEND_API_KEY")


class ResendEmailRepo:
    def send_email(self, subject: str, body: str, recipient: str):
        r = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": recipient,
            "subject": subject,
            "html": body
        })
