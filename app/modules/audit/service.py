import json
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditActorType, AuditLog
from app.modules.audit.repository import AuditLogRepository
from app.modules.audit.schema import AuditLogResponse


class AuditLogService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuditLogRepository(db)

    async def log(
        self,
        actor_type: AuditActorType,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        details: dict | None = None,
    ) -> AuditLog:
        request_id = structlog.contextvars.get_contextvars().get("request_id")
        entry = AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details or {}),
            request_id=request_id,
        )
        return await self.repo.create(entry)

    async def list_my_logs(self, user_id: UUID) -> list[AuditLogResponse]:
        entries = await self.repo.list_for_actor(user_id)
        return [
            AuditLogResponse(
                id=entry.id,
                actor_type=entry.actor_type,
                actor_id=entry.actor_id,
                action=entry.action,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                details=json.loads(entry.details),
                request_id=entry.request_id,
                created_at=entry.created_at,
            )
            for entry in entries
        ]
