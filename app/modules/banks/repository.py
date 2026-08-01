from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank import Bank


class BankRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, bank_id: UUID) -> Bank | None:
        stmt = select(Bank).where(Bank.id == bank_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Bank | None:
        stmt = select(Bank).where(Bank.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Bank]:
        stmt = select(Bank)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, bank: Bank) -> Bank:
        self.db.add(bank)
        await self.db.flush()
        await self.db.refresh(bank)
        return bank
