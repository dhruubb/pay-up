from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationChannel, NotificationStatus


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    channel: NotificationChannel
    message: str
    status: NotificationStatus
    created_at: datetime
