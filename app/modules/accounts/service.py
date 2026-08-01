import random
import string
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, DuplicateError, NotFoundError
from app.models.account import Account
from app.modules.accounts.repository import AccountRepository
from app.modules.accounts.schema import AccountCreateRequest
from app.modules.banks.repository import BankRepository


def _generate_account_number() -> str:
    return "".join(random.choices(string.digits, k=12))


class AccountService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AccountRepository(db)
        self.bank_repo = BankRepository(db)

    async def open_account(self, user_id: UUID, request: AccountCreateRequest) -> Account:
        bank = await self.bank_repo.get_by_id(request.bank_id)
        if not bank:
            raise NotFoundError("Bank")

        existing = await self.repo.get_by_user_and_bank(user_id, request.bank_id)
        if existing:
            raise DuplicateError("Account", "bank")

        account_number = _generate_account_number()
        while await self.repo.get_by_account_number(account_number):
            account_number = _generate_account_number()

        account = Account(
            user_id=user_id,
            bank_id=request.bank_id,
            account_number=account_number,
        )
        account = await self.repo.create(account)
        await self.db.commit()
        return account

    async def list_my_accounts(self, user_id: UUID) -> list[Account]:
        return await self.repo.list_for_user(user_id)

    async def get_account(self, user_id: UUID, account_id: UUID) -> Account:
        account = await self.repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account")
        if account.user_id != user_id:
            raise AuthorizationError()
        return account
