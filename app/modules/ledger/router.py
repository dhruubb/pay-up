from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.ledger.schema import TransferRequest, TransferResponse
from app.modules.ledger.service import LedgerService

router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.post(
    "/transfer",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
)
async def transfer(
    request: TransferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = LedgerService(db)
    debit_entry, credit_entry = await service.transfer(
        current_user.id,
        request.from_account_id,
        request.to_account_id,
        request.amount_paise,
    )
    return TransferResponse(
        debit_entry_id=debit_entry.id,
        credit_entry_id=credit_entry.id,
        amount_paise=request.amount_paise,
    )
