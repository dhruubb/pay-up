import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "bank_id", name="uq_accounts_user_bank"),
    )

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

    bank_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("banks.id"),
        index=True,
    )

    account_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False, length=20),
        default=AccountStatus.ACTIVE,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
