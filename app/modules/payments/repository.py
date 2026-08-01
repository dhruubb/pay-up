from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_accounts(self, account_ids: list[UUID]) -> list[Payment]:
        if not account_ids:
            return []
        stmt = (
            select(Payment)
            .where(
                or_(
                    Payment.sender_account_id.in_(account_ids),
                    Payment.receiver_account_id.in_(account_ids),
                )
            )
            .order_by(Payment.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment
