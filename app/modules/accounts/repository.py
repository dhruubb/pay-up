from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


class AccountRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, account_id: UUID) -> Account | None:
        stmt = select(Account).where(Account.id == account_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_and_bank(self, user_id: UUID, bank_id: UUID) -> Account | None:
        stmt = select(Account).where(
            Account.user_id == user_id,
            Account.bank_id == bank_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_account_number(self, account_number: str) -> Account | None:
        stmt = select(Account).where(Account.account_number == account_number)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[Account]:
        stmt = select(Account).where(Account.user_id == user_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, account: Account) -> Account:
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account
