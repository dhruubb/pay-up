from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.accounts.schema import AccountCreateRequest, AccountResponse
from app.modules.accounts.service import AccountService
from app.modules.ledger.schema import BalanceResponse, LedgerEntryResponse
from app.modules.ledger.service import LedgerService

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_account(
    request: AccountCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountService(db)
    account = await service.open_account(current_user.id, request)
    return AccountResponse.model_validate(account)


@router.get(
    "",
    response_model=list[AccountResponse],
)
async def list_my_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountService(db)
    accounts = await service.list_my_accounts(current_user.id)
    return [AccountResponse.model_validate(account) for account in accounts]


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
)
async def get_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AccountService(db)
    account = await service.get_account(current_user.id, account_id)
    return AccountResponse.model_validate(account)


@router.get(
    "/{account_id}/balance",
    response_model=BalanceResponse,
)
async def get_account_balance(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account_service = AccountService(db)
    await account_service.get_account(current_user.id, account_id)

    ledger_service = LedgerService(db)
    balance_paise = await ledger_service.get_balance_paise(account_id)
    return BalanceResponse(account_id=account_id, balance_paise=balance_paise)


@router.get(
    "/{account_id}/ledger",
    response_model=list[LedgerEntryResponse],
)
async def get_account_ledger(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    account_service = AccountService(db)
    await account_service.get_account(current_user.id, account_id)

    ledger_service = LedgerService(db)
    entries = await ledger_service.get_history(account_id)
    return [LedgerEntryResponse.model_validate(entry) for entry in entries]
