import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Vpa(Base):
    __tablename__ = "vpas"
    __table_args__ = (
        Index(
            "uq_vpas_primary_per_account",
            "account_id",
            unique=True,
            sqlite_where=text("is_primary = 1"),
        ),
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

    psp_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("psps.id"),
        index=True,
    )

    address: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
