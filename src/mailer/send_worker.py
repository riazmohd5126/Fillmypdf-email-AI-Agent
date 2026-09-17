from __future__ import annotations

import datetime as dt
import logging
import random
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from src import config
from src.db.base import SessionLocal
from src.db.models import (
    Enrollment,
    EnrollmentStatus,
    Message,
    MessageStatus,
    SequenceStep,
)
from src.mailer.gmail_client import GmailClient
from src.mailer.message_builder import build_mime_message
from src.mailer.pre_send_checks import PreSendOutcome, PreSendResult, run_pre_send_checks
from src.mailer.send_window import add_business_days, next_send_window_start

logger = logging.getLogger(__name__)


def fetch_due_enrollments(db: Session, *, limit: int = 5) -> list[Enrollment]:
    now = dt.datetime.now(dt.timezone.utc)
    stmt = (
        select(Enrollment)
        .where(Enrollment.status == EnrollmentStatus.active)
        .where(Enrollment.next_send_at.isnot(None))
        .where(Enrollment.next_send_at <= now)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(db.execute(stmt).scalars())


def get_next_message(db: Session, enrollment: Enrollment) -> Message | None:
    stmt = select(Message).where(
        Message.enrollment_id == enrollment.id,
        Message.step_number == enrollment.current_step + 1,
    )
    return db.execute(stmt).scalar_one_or_none()


def stop_same_domain_enrollments(db: Session, replied_enrollment: Enrollment) -> None:
    """A practice is never emailed again after anyone there has replied."""
    domain = replied_enrollment.lead.email.split("@")[-1].lower()
    stmt = select(Enrollment).where(Enrollment.status == EnrollmentStatus.active)
    for enr in db.execute(stmt).scalars():
        if enr.id != replied_enrollment.id and enr.lead.email.split("@")[-1].lower() == domain:
            enr.status = EnrollmentStatus.stopped
            enr.stop_reason = "same_domain_reply"
            enr.next_send_at = None
            db.add(enr)
    db.commit()


def apply_outcome(db: Session, enrollment: Enrollment, result: PreSendResult) -> None:
    if result.outcome == PreSendOutcome.STOP:
        enrollment.status = EnrollmentStatus.stopped
        enrollment.stop_reason = result.failed_check
        enrollment.next_send_at = None
    elif result.outcome == PreSendOutcome.MARK_REPLIED:
        enrollment.status = EnrollmentStatus.replied
        enrollment.next_send_at = None
        db.add(enrollment)
        db.commit()
        stop_same_domain_enrollments(db, enrollment)
        return
    elif result.outcome == PreSendOutcome.RESCHEDULE:
        enrollment.next_send_at = result.reschedule_at

    db.add(enrollment)
    db.commit()


def schedule_next_step(db: Session, enrollment: Enrollment) -> None:
    enrollment.current_step += 1
    next_step = db.execute(
        select(SequenceStep).where(
            SequenceStep.sequence_id == enrollment.sequence_id,
            SequenceStep.step_number == enrollment.current_step + 1,
        )
    ).scalar_one_or_none()

    if next_step is None:
        enrollment.status = EnrollmentStatus.completed
        enrollment.next_send_at = None
    else:
        due_date = add_business_days(dt.date.today(), next_step.delay_days)
        earliest = dt.datetime.combine(due_date, dt.time(8, 30), tzinfo=dt.timezone.utc)
        enrollment.next_send_at = next_send_window_start(earliest)

    db.add(enrollment)
    db.commit()


def record_sent(
    db: Session,
    message: Message,
    enrollment: Enrollment,
    *,
    gmail_message_id: str,
    thread_id: str,
    message_id_header: str,
) -> None:
    message.status = MessageStatus.sent
    message.gmail_message_id = gmail_message_id
    message.message_id_header = message_id_header
    message.sent_at = dt.datetime.now(dt.timezone.utc)

    if not enrollment.gmail_thread_id:
        enrollment.gmail_thread_id = thread_id
    if not enrollment.first_message_id_header:
        enrollment.first_message_id_header = message_id_header

    db.add(message)
    db.add(enrollment)
    db.commit()


def today_sent_count(db: Session) -> int:
    start_of_day = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = select(Message).where(Message.status == MessageStatus.sent, Message.sent_at >= start_of_day)
    return len(list(db.execute(stmt).scalars()))


def last_sent_at(db: Session) -> dt.datetime | None:
    stmt = (
        select(Message.sent_at)
        .where(Message.status == MessageStatus.sent)
        .order_by(Message.sent_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def run_send_cycle() -> None:
    """One pass of the worker loop (design doc section 6.2).

    Meant to be called every ~10 minutes by a scheduler (Render Cron Job
    hitting an internal endpoint, per the doc) — wiring that trigger up is a
    later step; this function is the part that actually sends.
    """
    if config.KILL_SWITCH:
        logger.info("kill switch is on; skipping send cycle")
        return

    db = SessionLocal()
    try:
        gmail = GmailClient()
        due = fetch_due_enrollments(db, limit=5)
        sent_today = today_sent_count(db)

        for enrollment in due:
            message = get_next_message(db, enrollment)
            if message is None:
                enrollment.status = EnrollmentStatus.stopped
                enrollment.stop_reason = "no_message_for_step"
                db.add(enrollment)
                db.commit()
                continue

            result = run_pre_send_checks(
                db,
                enrollment,
                message,
                # inbox watcher (build plan item 5) not built yet; no-ops until it lands
                sync_inbox_if_stale=lambda _minutes: None,
                last_inbox_sync_at=None,
                has_new_reply=lambda _thread_id: False,
                last_send_at=last_sent_at(db),
                today_sent_count=sent_today,
            )

            if not result.ok:
                apply_outcome(db, enrollment, result)
                continue

            message.status = MessageStatus.sending
            db.add(message)
            db.commit()

            mime_message, message_id_header = build_mime_message(
                to_email=enrollment.lead.email,
                to_name=enrollment.lead.contact_name,
                subject=message.subject,
                body_text=message.body_text,
                enrollment_id=str(enrollment.id),
                thread_subject_prefix=enrollment.current_step > 0,
                in_reply_to=enrollment.first_message_id_header,
                references=enrollment.first_message_id_header,
            )

            try:
                sent = gmail.send(mime_message, thread_id=enrollment.gmail_thread_id)
            except Exception as exc:  # noqa: BLE001 — any send failure must not crash the cycle
                logger.exception("send failed for enrollment %s", enrollment.id)
                message.status = MessageStatus.failed
                message.error = str(exc)
                db.add(message)
                db.commit()
                continue

            record_sent(
                db, message, enrollment,
                gmail_message_id=sent.message_id,
                thread_id=sent.thread_id,
                message_id_header=message_id_header,
            )
            schedule_next_step(db, enrollment)
            sent_today += 1

            time.sleep(random.uniform(config.MIN_SEND_SPACING_SECONDS, config.MAX_SEND_SPACING_SECONDS))
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_send_cycle()
