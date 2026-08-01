from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentStatus
from app.models.payment_event import PaymentEventType


class PaymentCreateRequest(BaseModel):
    sender_vpa: str
    receiver_vpa: str
    amount_paise: int = Field(gt=0)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender_account_id: UUID
    receiver_account_id: UUID
    initiated_by_psp_id: UUID
    amount_paise: int
    status: PaymentStatus
    failure_reason: str | None
    created_at: datetime
    completed_at: datetime | None


class PaymentEventResponse(BaseModel):
    id: UUID
    event_type: PaymentEventType
    payload: dict[str, Any]
    published_at: datetime | None
    created_at: datetime
