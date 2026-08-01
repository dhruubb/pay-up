from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.audit_log import AuditActorType


class AuditLogResponse(BaseModel):
    id: UUID
    actor_type: AuditActorType
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    details: dict[str, Any]
    request_id: str | None
    created_at: datetime
