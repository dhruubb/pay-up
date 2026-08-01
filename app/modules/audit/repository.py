from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, entry: AuditLog) -> AuditLog:
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def list_for_actor(self, actor_id: UUID) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
