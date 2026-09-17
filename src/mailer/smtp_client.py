from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Optional

from src import config
from src.mailer.base_client import EmailSendResult


class SMTPClient:
    """Generic SMTP sender — e.g. for a Yahoo Mail mailbox during early testing.

    Not a substitute for the Gmail API client for real cold-email volume: no
    server-side thread_id, no List-Unsubscribe one-click support the way
    Gmail's API gives it, and consumer webmail providers apply aggressive
    spam filtering to repetitive sending. Threading still works here through
    the In-Reply-To/References/Message-ID headers message_builder sets.
    """

    def __init__(self) -> None:
        if not all([config.SMTP_HOST, config.SMTP_PORT, config.SMTP_USERNAME, config.SMTP_PASSWORD]):
            raise RuntimeError("SMTP credentials are not configured")

    def send(self, mime_message: MIMEText, thread_id: Optional[str] = None) -> EmailSendResult:
        message_id = mime_message["Message-ID"]
        _, from_addr = parseaddr(mime_message["From"])
        _, to_addr = parseaddr(mime_message["To"])

        if config.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30)

        try:
            if not config.SMTP_USE_SSL:
                server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.sendmail(from_addr, [to_addr], mime_message.as_string())
        finally:
            server.quit()

        return EmailSendResult(message_id=message_id, thread_id=None)
