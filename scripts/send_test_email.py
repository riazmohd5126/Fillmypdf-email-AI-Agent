"""Send a single test email using whatever provider is configured in .env.

Doesn't touch the database — just proves the Gmail/SMTP credentials and
message building work end to end. Run from anywhere:

    python scripts/send_test_email.py you@example.com
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mailer.message_builder import build_mime_message  # noqa: E402
from src.mailer.send_worker import get_email_client  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/send_test_email.py <to_email>")
        sys.exit(1)

    to_email = sys.argv[1]
    mime_message, message_id = build_mime_message(
        to_email=to_email,
        to_name=None,
        subject="FillMyPDF sending engine - test email",
        body_text="This is a test send from the FillMyPDF cold email sending engine.",
        enrollment_id="test-send",
    )

    client = get_email_client()
    result = client.send(mime_message)
    print(f"Sent. Message-ID: {result.message_id}, thread_id: {result.thread_id}")


if __name__ == "__main__":
    main()
