from __future__ import annotations

from dataclasses import dataclass
from email.mime.text import MIMEText
from typing import Optional, Protocol


@dataclass
class EmailSendResult:
    message_id: str
    thread_id: Optional[str] = None


class EmailClient(Protocol):
    """Common interface the send worker calls, regardless of provider.

    `thread_id` is Gmail's server-side concept for grouping a thread in the
    Gmail UI — providers without an equivalent (e.g. plain SMTP) accept and
    ignore it; threading for those still works via the In-Reply-To/
    References/Message-ID headers message_builder already sets.
    """

    def send(self, mime_message: MIMEText, thread_id: Optional[str] = None) -> EmailSendResult: ...
