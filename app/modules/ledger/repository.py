from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ledger_entry import LedgerEntry, LedgerEntryType


class LedgerRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance_paise(self, account_id: UUID) -> int:
        credit_stmt = select(func.coalesce(func.sum(LedgerEntry.amount_paise), 0)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.entry_type == LedgerEntryType.CREDIT,
        )
        debit_stmt = select(func.coalesce(func.sum(LedgerEntry.amount_paise), 0)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.entry_type == LedgerEntryType.DEBIT,
        )
        credit_total = (await self.db.execute(credit_stmt)).scalar_one()
        debit_total = (await self.db.execute(debit_stmt)).scalar_one()
        return credit_total - debit_total

    async def list_for_account(self, account_id: UUID) -> list[LedgerEntry]:
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.account_id == account_id)
            .order_by(LedgerEntry.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, entry: LedgerEntry) -> LedgerEntry:
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry
