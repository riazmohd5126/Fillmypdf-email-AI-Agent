from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from src import config
from src.db.models import (
    ApprovalStatus,
    Enrollment,
    EnrollmentStatus,
    Message,
    MessageStatus,
    Suppression,
)
from src.mailer.message_builder import build_footer
from src.mailer.send_window import is_within_send_window, next_send_window_start


def _as_aware_utc(value: Optional[dt.datetime]) -> Optional[dt.datetime]:
    """SQLite drops tzinfo on round-trip even for DateTime(timezone=True) columns;
    Postgres does not. Treat a naive value read back from either as UTC."""
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=dt.timezone.utc)


class PreSendOutcome:
    SEND = "send"
    STOP = "stop"  # checks 1, 2, 3, 4, 5, 9 fail -> stop or flag the enrollment
    MARK_REPLIED = "mark_replied"  # check 6 fails
    RESCHEDULE = "reschedule"  # checks 7, 8 fail


@dataclass
class PreSendResult:
    ok: bool
    outcome: str
    failed_check: Optional[str] = None
    reschedule_at: Optional[dt.datetime] = None


def run_pre_send_checks(
    db: Session,
    enrollment: Enrollment,
    message: Message,
    *,
    sync_inbox_if_stale: Callable[[int], None],
    last_inbox_sync_at: Optional[dt.datetime],
    has_new_reply: Callable[[str], bool],
    last_send_at: Optional[dt.datetime],
    today_sent_count: int,
) -> PreSendResult:
    """Runs every check in Section 6.1, in order, immediately before a send.

    `sync_inbox_if_stale` and `has_new_reply` are placeholders for the inbox
    watcher (design doc build plan item 5, not yet built) — callers can pass
    no-ops until it lands; check 6 then always passes.
    """
    now = dt.datetime.now(dt.timezone.utc)

    # 1. Global kill switch / mailbox pause
    if config.KILL_SWITCH:
        return PreSendResult(False, PreSendOutcome.STOP, "kill_switch")

    # 2. Enrollment still active and step not already sent
    if enrollment.status != EnrollmentStatus.active:
        return PreSendResult(False, PreSendOutcome.STOP, "enrollment_not_active")
    if message.status == MessageStatus.sent:
        return PreSendResult(False, PreSendOutcome.STOP, "already_sent")

    # 3. Message exists and is approved
    if message.approval_status != ApprovalStatus.approved:
        return PreSendResult(False, PreSendOutcome.STOP, "not_approved")

    # 4. Email and its domain are not suppressed
    lead = enrollment.lead
    email = lead.email.lower()
    domain = email.split("@")[-1]
    suppressed = db.query(Suppression).filter(Suppression.value.in_([email, domain])).first()
    if suppressed:
        return PreSendResult(False, PreSendOutcome.STOP, "suppressed")

    # 5. Email verified within the last 90 days
    verified_at = _as_aware_utc(lead.email_verified_at)
    if verified_at is None or (now - verified_at) > dt.timedelta(days=90):
        return PreSendResult(False, PreSendOutcome.STOP, "not_verified")

    # 6. No reply since the last inbox sync (force a sync if it's stale)
    last_inbox_sync_at = _as_aware_utc(last_inbox_sync_at)
    if last_inbox_sync_at is None or (now - last_inbox_sync_at) > dt.timedelta(minutes=15):
        sync_inbox_if_stale(15)
    if enrollment.gmail_thread_id and has_new_reply(enrollment.gmail_thread_id):
        return PreSendResult(False, PreSendOutcome.MARK_REPLIED, "reply_detected")

    # 7. Inside the lead's send window
    tz = ZoneInfo(lead.timezone or "America/New_York")
    local_now = now.astimezone(tz)
    if not is_within_send_window(local_now):
        return PreSendResult(
            False, PreSendOutcome.RESCHEDULE, "outside_send_window",
            reschedule_at=next_send_window_start(local_now),
        )

    # 8. Daily cap and randomized spacing since the last send
    if today_sent_count >= config.DAILY_CAP:
        tomorrow = local_now + dt.timedelta(days=1)
        return PreSendResult(
            False, PreSendOutcome.RESCHEDULE, "daily_cap_reached",
            reschedule_at=next_send_window_start(tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)),
        )
    last_send_at = _as_aware_utc(last_send_at)
    if last_send_at is not None:
        min_gap = dt.timedelta(seconds=random.randint(config.MIN_SEND_SPACING_SECONDS, config.MAX_SEND_SPACING_SECONDS))
        if now - last_send_at < min_gap:
            return PreSendResult(
                False, PreSendOutcome.RESCHEDULE, "send_spacing",
                reschedule_at=last_send_at + min_gap,
            )

    # 9. Template lint: the composed body must carry the address and opt-out line
    composed_body = (message.body_text + build_footer(str(enrollment.id), lead.email)).lower()
    if not config.PHYSICAL_ADDRESS or config.PHYSICAL_ADDRESS.lower() not in composed_body:
        return PreSendResult(False, PreSendOutcome.STOP, "missing_physical_address")
    if "unsubscribe" not in composed_body:
        return PreSendResult(False, PreSendOutcome.STOP, "missing_unsubscribe_line")

    return PreSendResult(True, PreSendOutcome.SEND)
