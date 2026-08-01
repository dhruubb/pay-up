from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.psp import Psp


class PspRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, psp_id: UUID) -> Psp | None:
        stmt = select(Psp).where(Psp.id == psp_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Psp | None:
        stmt = select(Psp).where(Psp.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Psp]:
        stmt = select(Psp)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, psp: Psp) -> Psp:
        self.db.add(psp)
        await self.db.flush()
        await self.db.refresh(psp)
        return psp
