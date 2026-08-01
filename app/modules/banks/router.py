from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.banks.schema import BankCreateRequest, BankResponse
from app.modules.banks.service import BankService

router = APIRouter(prefix="/banks", tags=["Banks"])


@router.post(
    "",
    response_model=BankResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bank(
    request: BankCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BankService(db)
    bank = await service.create_bank(request)
    return BankResponse.model_validate(bank)


@router.get(
    "",
    response_model=list[BankResponse],
)
async def list_banks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BankService(db)
    banks = await service.list_banks()
    return [BankResponse.model_validate(bank) for bank in banks]


@router.get(
    "/{bank_id}",
    response_model=BankResponse,
)
async def get_bank(
    bank_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BankService(db)
    bank = await service.get_bank(bank_id)
    return BankResponse.model_validate(bank)
