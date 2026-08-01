import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class AuditActorType(str, enum.Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"


class AuditLog(Base):
    """
    Generic compliance/security trail. Deliberately has no FK constraints on
    actor_id/resource_id — it references heterogeneous resource types (User,
    Payment, ...) that a single FK can't span, which is normal for an audit
    table.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    actor_type: Mapped[AuditActorType] = mapped_column(
        Enum(AuditActorType, native_enum=False, length=10),
    )

    # Nullable — e.g. a failed login against an email with no matching user
    # has no real actor to attribute it to, but the attempt is still worth
    # recording.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)

    action: Mapped[str] = mapped_column(String(50), index=True)

    resource_type: Mapped[str] = mapped_column(String(50))

    resource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)

    details: Mapped[str] = mapped_column(Text)

    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
