from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment_event import PaymentEvent, PaymentEventType


class PaymentEventRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self,
        payment_id: UUID,
        event_type: PaymentEventType,
        payload: str,
        request_id: str | None = None,
    ) -> PaymentEvent:
        event = PaymentEvent(
            payment_id=payment_id,
            event_type=event_type,
            payload=payload,
            request_id=request_id,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def list_for_payment(self, payment_id: UUID) -> list[PaymentEvent]:
        stmt = (
            select(PaymentEvent)
            .where(PaymentEvent.payment_id == payment_id)
            .order_by(PaymentEvent.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
