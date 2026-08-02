import asyncio
from contextlib import AsyncExitStack, asynccontextmanager
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

# Per-account asyncio locks serializing the "read balance, then write an
# entry based on it" critical section. Without this, two concurrent requests
# against the same account can both read the same pre-write balance and both
# pass an insufficient-funds check that should only let one of them through —
# proven by tests/test_ledger.py::test_concurrent_transfers_never_overdraw_account,
# which reliably let a 100_000-paise account go to -100_000 before this fix.
#
# This is a process-local lock — correct for this app's actual deployment (a
# single Uvicorn process). It stops being sufficient the moment you run
# multiple worker processes or instances; at that point you'd need a
# distributed lock (e.g. Redis) or move to Postgres row locking
# (`SELECT ... FOR UPDATE`). Also note the lock registry below is never
# pruned, so it grows by one entry per distinct account ever touched — fine
# at this app's scale, not fine unbounded.
_account_locks: dict[UUID, asyncio.Lock] = {}
_registry_guard = asyncio.Lock()


async def _get_lock(account_id: UUID) -> asyncio.Lock:
    async with _registry_guard:
        lock = _account_locks.get(account_id)
        if lock is None:
            lock = asyncio.Lock()
            _account_locks[account_id] = lock
        return lock


class LedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = LedgerRepository(db)
        self.account_repo = AccountRepository(db)

    async def get_balance_paise(self, account_id: UUID) -> int:
        return await self.repo.get_balance_paise(account_id)

    async def get_history(self, account_id: UUID) -> list[LedgerEntry]:
        return await self.repo.list_for_account(account_id)

    @asynccontextmanager
    async def locked(self, *account_ids: UUID):
        """
        Serializes ledger writes to the given account(s). Always acquires in
        a fixed (sorted) order so two transfers moving money in opposite
        directions between the same two accounts can't deadlock on each
        other's locks.
        """
        ordered = sorted(set(account_ids), key=str)
        async with AsyncExitStack() as stack:
            for account_id in ordered:
                lock = await _get_lock(account_id)
                await stack.enter_async_context(lock)
            yield

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

        Callers MUST hold `self.locked(account_id)` for the full span from
        before this call through their commit — see transfer() below for the
        pattern. Calling this without the lock reintroduces the race this
        class exists to prevent.
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

        async with self.locked(from_account_id, to_account_id):
            debit_entry = await self.post_entry(from_account_id, LedgerEntryType.DEBIT, amount_paise)
            await self.db.flush()
            credit_entry = await self.post_entry(to_account_id, LedgerEntryType.CREDIT, amount_paise)
            await self.db.commit()

        return debit_entry, credit_entry
