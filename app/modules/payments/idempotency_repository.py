from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey, IdempotencyStatus


class IdempotencyKeyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_key(self, key: str) -> IdempotencyKey | None:
        stmt = select(IdempotencyKey).where(IdempotencyKey.key == key)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, key: str, request_hash: str) -> IdempotencyKey:
        record = IdempotencyKey(
            key=key,
            request_hash=request_hash,
            status=IdempotencyStatus.IN_PROGRESS,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record
