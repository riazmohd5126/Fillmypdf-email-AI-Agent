from __future__ import annotations

import hashlib
import hmac
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, make_msgid

from src import config


def generate_unsubscribe_token(enrollment_id: str, email: str) -> str:
    if not config.UNSUBSCRIBE_SECRET:
        raise RuntimeError("UNSUBSCRIBE_SECRET is not configured")
    payload = f"{enrollment_id}:{email.lower()}".encode()
    digest = hmac.new(config.UNSUBSCRIBE_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return f"{enrollment_id}.{digest}"


def unsubscribe_url(enrollment_id: str, email: str) -> str:
    token = generate_unsubscribe_token(enrollment_id, email)
    return f"{config.UNSUBSCRIBE_BASE_URL}/{token}"


def build_footer(enrollment_id: str, email: str) -> str:
    address = config.PHYSICAL_ADDRESS or ""
    return (
        f"\n\n--\n{address}\n"
        f'Not relevant? Reply "no thanks" or unsubscribe here: {unsubscribe_url(enrollment_id, email)}'
    )


def build_mime_message(
    *,
    to_email: str,
    to_name: str | None,
    subject: str,
    body_text: str,
    enrollment_id: str,
    thread_subject_prefix: bool = False,
    in_reply_to: str | None = None,
    references: str | None = None,
) -> tuple[MIMEText, str]:
    """Build the MIME message for one send, per design doc section 7.2-7.3.

    Plain text only, one footer with the physical address and opt-out line,
    and (for follow-up steps) the headers Gmail and the recipient's client
    need to thread the message under step 1.
    """
    if not config.SENDER_EMAIL:
        raise RuntimeError("SENDER_EMAIL is not configured")

    full_subject = f"Re: {subject}" if thread_subject_prefix else subject
    full_body = body_text.rstrip() + build_footer(enrollment_id, to_email)

    msg = MIMEText(full_body, "plain")
    msg["From"] = formataddr((config.SENDER_NAME, config.SENDER_EMAIL))
    msg["To"] = formataddr((to_name or "", to_email))
    msg["Subject"] = str(Header(full_subject, "utf-8"))

    message_id_header = make_msgid(domain=config.SENDER_EMAIL.split("@")[-1])
    msg["Message-ID"] = message_id_header

    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

    unsub_url = unsubscribe_url(enrollment_id, to_email)
    msg["List-Unsubscribe"] = f"<mailto:{config.SENDER_EMAIL}?subject=unsubscribe>, <{unsub_url}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    return msg, message_id_header
