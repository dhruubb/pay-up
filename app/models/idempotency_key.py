import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class IdempotencyStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    request_hash: Mapped[str] = mapped_column(String(64))

    status: Mapped[IdempotencyStatus] = mapped_column(
        Enum(IdempotencyStatus, native_enum=False, length=20),
        default=IdempotencyStatus.IN_PROGRESS,
    )

    # JSON-encoded {"outcome": "success"|"error", ...} — the exact response
    # (or error) to replay if this key is reused with the same payload.
    response_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
