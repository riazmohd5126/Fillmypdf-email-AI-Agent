from __future__ import annotations

import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src import config

# gmail.modify is only needed if the engine starts labeling messages (design doc 7.1)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


class GmailSendResult:
    def __init__(self, message_id: str, thread_id: str):
        self.message_id = message_id
        self.thread_id = thread_id


class GmailClient:
    """Thin wrapper around the Gmail API, authorized once as the outreach mailbox.

    Authentication errors should pause all sending and alert immediately
    rather than retrying in a tight loop (design doc section 7.4) — that
    policy lives in the send worker, not here.
    """

    def __init__(self) -> None:
        if not all([config.GMAIL_CLIENT_ID, config.GMAIL_CLIENT_SECRET, config.GMAIL_REFRESH_TOKEN]):
            raise RuntimeError("Gmail OAuth credentials are not configured")

        self._credentials = Credentials(
            token=None,
            refresh_token=config.GMAIL_REFRESH_TOKEN,
            client_id=config.GMAIL_CLIENT_ID,
            client_secret=config.GMAIL_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        self._service = build("gmail", "v1", credentials=self._credentials, cache_discovery=False)

    def send(self, mime_message: MIMEText, thread_id: str | None = None) -> GmailSendResult:
        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        body = {"raw": raw}
        if thread_id:
            body["threadId"] = thread_id

        sent = self._service.users().messages().send(userId="me", body=body).execute()
        return GmailSendResult(message_id=sent["id"], thread_id=sent["threadId"])
