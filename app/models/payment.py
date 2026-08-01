import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    sender_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id"),
        index=True,
    )

    receiver_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id"),
        index=True,
    )

    initiated_by_psp_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("psps.id"),
    )

    amount_paise: Mapped[int] = mapped_column(BigInteger)

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=20),
        default=PaymentStatus.INITIATED,
    )

    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
