import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class NotificationChannel(str, enum.Enum):
    PUSH = "PUSH"


class NotificationStatus(str, enum.Enum):
    SENT = "SENT"
    FAILED = "FAILED"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id"),
        index=True,
    )

    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, native_enum=False, length=10),
        default=NotificationChannel.PUSH,
    )

    message: Mapped[str] = mapped_column(String(255))

    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, native_enum=False, length=10),
        default=NotificationStatus.SENT,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
