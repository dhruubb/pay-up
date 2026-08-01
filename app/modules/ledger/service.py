from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AccountNotActiveError,
    AuthorizationError,
    InsufficientFundsError,
    InvalidOperationError,
    NotFoundError,
)
from app.models.account import AccountStatus
from app.models.ledger_entry import LedgerEntry, LedgerEntryType
from app.modules.accounts.repository import AccountRepository
from app.modules.ledger.repository import LedgerRepository


class LedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LedgerRepository(db)
        self.account_repo = AccountRepository(db)

    async def get_balance_paise(self, account_id: UUID) -> int:
        return await self.repo.get_balance_paise(account_id)

    async def get_history(self, account_id: UUID) -> list[LedgerEntry]:
        return await self.repo.list_for_account(account_id)

    async def post_entry(
        self,
        account_id: UUID,
        entry_type: LedgerEntryType,
        amount_paise: int,
        payment_id: UUID | None = None,
    ) -> LedgerEntry:
        """
        Post a single ledger leg. Does not commit — callers control the
        transaction boundary, since payments post each leg (debit, credit)
        in its own separate commit to simulate sender/receiver bank being
        distinct systems (see PaymentService for why).
        """
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account", str(account_id))
        if account.status != AccountStatus.ACTIVE:
            raise AccountNotActiveError(f"Account {account_id} is not active")

        balance = await self.repo.get_balance_paise(account_id)

        if entry_type == LedgerEntryType.DEBIT:
            if amount_paise > balance:
                raise InsufficientFundsError()
            new_balance = balance - amount_paise
        else:
            new_balance = balance + amount_paise

        entry = LedgerEntry(
            account_id=account_id,
            payment_id=payment_id,
            entry_type=entry_type,
            amount_paise=amount_paise,
            balance_after_paise=new_balance,
        )
        return await self.repo.create(entry)

    async def transfer(
        self,
        user_id: UUID,
        from_account_id: UUID,
        to_account_id: UUID,
        amount_paise: int,
    ) -> tuple[LedgerEntry, LedgerEntry]:
        if from_account_id == to_account_id:
            raise InvalidOperationError("Cannot transfer to the same account")

        from_account = await self.account_repo.get_by_id(from_account_id)
        if not from_account:
            raise NotFoundError("Account", str(from_account_id))
        if from_account.user_id != user_id:
            raise AuthorizationError("You can only send money from your own account")

        to_account = await self.account_repo.get_by_id(to_account_id)
        if not to_account:
            raise NotFoundError("Account", str(to_account_id))

        debit_entry = await self.post_entry(from_account_id, LedgerEntryType.DEBIT, amount_paise)

        # Flush the debit before creating the credit so the two writes hit the
        # DB in a fixed order. SQLite's single-writer lock already serializes
        # the whole transfer against concurrent transfers — on Postgres this
        # ordering alone wouldn't be enough; you'd also need
        # `SELECT ... FOR UPDATE` on both accounts before reading their balances.
        await self.db.flush()

        credit_entry = await self.post_entry(to_account_id, LedgerEntryType.CREDIT, amount_paise)

        await self.db.commit()
        return debit_entry, credit_entry
