from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, DuplicateError, NotFoundError
from app.models.account import Account
from app.models.vpa import Vpa
from app.modules.accounts.repository import AccountRepository
from app.modules.psps.repository import PspRepository
from app.modules.vpas.repository import VpaRepository
from app.modules.vpas.schema import VpaCreateRequest


class VpaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VpaRepository(db)
        self.account_repo = AccountRepository(db)
        self.psp_repo = PspRepository(db)

    async def _get_owned_account(self, user_id: UUID, account_id: UUID) -> Account:
        account = await self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account")
        if account.user_id != user_id:
            raise AuthorizationError()
        return account

    async def create_vpa(self, user_id: UUID, request: VpaCreateRequest) -> Vpa:
        await self._get_owned_account(user_id, request.account_id)

        psp = await self.psp_repo.get_by_id(request.psp_id)
        if not psp:
            raise NotFoundError("PSP")

        existing = await self.repo.get_by_address(request.address)
        if existing:
            raise DuplicateError("VPA", "address")

        current_primary = await self.repo.get_primary_for_account(request.account_id)

        vpa = Vpa(
            account_id=request.account_id,
            psp_id=request.psp_id,
            address=request.address,
            is_primary=current_primary is None,
        )
        vpa = await self.repo.create(vpa)
        await self.db.commit()
        return vpa

    async def list_my_vpas(self, user_id: UUID) -> list[Vpa]:
        return await self.repo.list_for_user(user_id)

    async def get_vpa(self, user_id: UUID, vpa_id: UUID) -> Vpa:
        vpa = await self.repo.get_by_id(vpa_id)
        if not vpa:
            raise NotFoundError("VPA")
        await self._get_owned_account(user_id, vpa.account_id)
        return vpa

    async def set_primary(self, user_id: UUID, vpa_id: UUID) -> Vpa:
        vpa = await self.repo.get_by_id(vpa_id)
        if not vpa:
            raise NotFoundError("VPA")
        await self._get_owned_account(user_id, vpa.account_id)

        if not vpa.is_primary:
            current_primary = await self.repo.get_primary_for_account(vpa.account_id)
            if current_primary:
                current_primary.is_primary = False
                # Flush the demotion before promoting the new one — otherwise
                # SQLAlchemy may batch both UPDATEs into one executemany() call,
                # and SQLite can apply them in an order that briefly has two
                # rows with is_primary=1, violating the partial unique index.
                await self.db.flush()
            vpa.is_primary = True
            await self.db.commit()
            await self.db.refresh(vpa)

        return vpa

    async def resolve(self, address: str) -> Vpa:
        vpa = await self.repo.get_by_address(address.lower())
        if not vpa:
            raise NotFoundError("VPA")
        return vpa
