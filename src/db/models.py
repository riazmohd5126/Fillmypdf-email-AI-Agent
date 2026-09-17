import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from src.db.base import Base


def _uuid_pk() -> Column:
    return Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))


class EnrollmentStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    replied = "replied"
    bounced = "bounced"
    unsubscribed = "unsubscribed"
    completed = "completed"
    stopped = "stopped"


class SequenceMode(str, enum.Enum):
    new_thread = "new_thread"
    reply_in_thread = "reply_in_thread"


class ApprovalStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    rejected = "rejected"


class MessageStatus(str, enum.Enum):
    queued = "queued"
    sending = "sending"
    sent = "sent"
    failed = "failed"


class SuppressionKind(str, enum.Enum):
    email = "email"
    domain = "domain"


class SuppressionReason(str, enum.Enum):
    unsubscribe = "unsubscribe"
    hard_bounce = "hard_bounce"
    complaint = "complaint"
    manual = "manual"
    customer = "customer"


class Lead(Base):
    __tablename__ = "leads"

    id = _uuid_pk()
    practice_name = Column(Text, nullable=False)
    npi = Column(Text, nullable=True)
    specialty = Column(Text, nullable=True)
    contact_name = Column(Text, nullable=True)
    contact_role = Column(Text, nullable=True)
    email = Column(String, nullable=False, unique=True)  # lowercased before insert
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    city = Column(Text, nullable=True)
    state = Column(Text, nullable=True)
    timezone = Column(Text, nullable=False, default="America/New_York")
    source = Column(Text, nullable=False, default="manual")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    enrollments = relationship("Enrollment", back_populates="lead")


class Sequence(Base):
    __tablename__ = "sequences"

    id = _uuid_pk()
    name = Column(Text, nullable=False)

    steps = relationship(
        "SequenceStep", back_populates="sequence", order_by="SequenceStep.step_number"
    )


class SequenceStep(Base):
    __tablename__ = "sequence_steps"
    __table_args__ = (UniqueConstraint("sequence_id", "step_number"),)

    id = _uuid_pk()
    sequence_id = Column(String(36), ForeignKey("sequences.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    delay_days = Column(Integer, nullable=False, default=0)  # business days after previous step
    mode = Column(SAEnum(SequenceMode), nullable=False)
    template_subject = Column(Text, nullable=True)
    template_body = Column(Text, nullable=True)

    sequence = relationship("Sequence", back_populates="steps")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("lead_id", "sequence_id"),)

    id = _uuid_pk()
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False)
    sequence_id = Column(String(36), ForeignKey("sequences.id"), nullable=False)
    status = Column(SAEnum(EnrollmentStatus), nullable=False, default=EnrollmentStatus.active)
    current_step = Column(Integer, nullable=False, default=0)  # last step successfully sent
    next_send_at = Column(DateTime(timezone=True), nullable=True)
    gmail_thread_id = Column(Text, nullable=True)
    first_message_id_header = Column(Text, nullable=True)  # RFC Message-ID of step 1, for threading
    stop_reason = Column(Text, nullable=True)

    lead = relationship("Lead", back_populates="enrollments")
    sequence = relationship("Sequence")
    messages = relationship("Message", back_populates="enrollment")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("enrollment_id", "step_number"),)

    id = _uuid_pk()
    enrollment_id = Column(String(36), ForeignKey("enrollments.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    subject = Column(Text, nullable=False)
    body_text = Column(Text, nullable=False)  # approved draft, before the engine-appended footer
    approval_status = Column(SAEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.draft)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(Text, nullable=True)
    status = Column(SAEnum(MessageStatus), nullable=False, default=MessageStatus.queued)
    gmail_message_id = Column(Text, nullable=True)
    message_id_header = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)

    enrollment = relationship("Enrollment", back_populates="messages")


class Suppression(Base):
    __tablename__ = "suppression"

    value = Column(String, primary_key=True)  # an email address or a whole domain, lowercased
    kind = Column(SAEnum(SuppressionKind), nullable=False)
    reason = Column(SAEnum(SuppressionReason), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # entries are never deleted automatically
