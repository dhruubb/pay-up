import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class PaymentEventType(str, enum.Enum):
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    DEBITED = "DEBITED"
    CREDITED = "CREDITED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PaymentEvent(Base):
    """
    Outbox row for a payment state transition. Written in the same commit as
    the transition it records, so it's durable iff the transition committed.
    A separate worker (app/workers/outbox_publisher.py) relays unpublished
    rows to Kafka — this avoids the dual-write problem of "commit to DB and
    publish to Kafka" not being atomic.
    """

    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id"),
        index=True,
    )

    event_type: Mapped[PaymentEventType] = mapped_column(
        Enum(PaymentEventType, native_enum=False, length=20),
    )

    payload: Mapped[str] = mapped_column(Text)

    # The API request that caused this event, so logs can be correlated
    # across the API process and the two worker processes downstream.
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # NULL until the outbox publisher successfully relays this row to Kafka.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
