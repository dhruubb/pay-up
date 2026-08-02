from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.rate_limit import rate_limit_by_user
from app.db.session import get_db
from app.models.user import User
from app.modules.payments.schema import (
    PaymentCreateRequest,
    PaymentEventResponse,
    PaymentResponse,
)
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_by_user("payment_initiate", limit=10, window_seconds=60))],
)
async def initiate_payment(
    request: PaymentCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.initiate_payment(current_user.id, idempotency_key, request)


@router.get(
    "",
    response_model=list[PaymentResponse],
)
async def list_my_payments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.list_my_payments(current_user.id)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
async def get_payment(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.get_payment(current_user.id, payment_id)


@router.get(
    "/{payment_id}/events",
    response_model=list[PaymentEventResponse],
)
async def get_payment_events(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.get_events(current_user.id, payment_id)
