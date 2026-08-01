from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.vpa import Vpa


class VpaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, vpa_id: UUID) -> Vpa | None:
        stmt = select(Vpa).where(Vpa.id == vpa_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_address(self, address: str) -> Vpa | None:
        stmt = select(Vpa).where(Vpa.address == address)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_primary_for_account(self, account_id: UUID) -> Vpa | None:
        stmt = select(Vpa).where(
            Vpa.account_id == account_id,
            Vpa.is_primary.is_(True),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[Vpa]:
        stmt = (
            select(Vpa)
            .join(Account, Vpa.account_id == Account.id)
            .where(Account.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, vpa: Vpa) -> Vpa:
        self.db.add(vpa)
        await self.db.flush()
        await self.db.refresh(vpa)
        return vpa
