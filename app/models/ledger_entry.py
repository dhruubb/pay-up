import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class LedgerEntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_paise > 0", name="ck_ledger_entries_amount_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("accounts.id"),
        index=True,
    )

    # Nullable because not every ledger entry originates from a payment (e.g.
    # the ad-hoc internal /ledger/transfer endpoint, or test fixtures).
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id"),
        nullable=True,
        index=True,
    )

    entry_type: Mapped[LedgerEntryType] = mapped_column(
        Enum(LedgerEntryType, native_enum=False, length=10),
    )

    # Stored in paise (smallest INR unit), never as float/Decimal — SQLite has
    # no real fixed-point storage and would silently fall back to floating
    # point, which is unacceptable for money.
    amount_paise: Mapped[int] = mapped_column(BigInteger)

    balance_after_paise: Mapped[int] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
