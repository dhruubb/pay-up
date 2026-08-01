from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateError, NotFoundError
from app.models.bank import Bank
from app.modules.banks.repository import BankRepository
from app.modules.banks.schema import BankCreateRequest


class BankService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BankRepository(db)

    async def create_bank(self, request: BankCreateRequest) -> Bank:
        existing = await self.repo.get_by_code(request.code)
        if existing:
            raise DuplicateError("Bank", "code")

        bank = Bank(name=request.name, code=request.code)
        bank = await self.repo.create(bank)
        await self.db.commit()
        return bank

    async def list_banks(self) -> list[Bank]:
        return await self.repo.list_all()

    async def get_bank(self, bank_id: UUID) -> Bank:
        bank = await self.repo.get_by_id(bank_id)
        if not bank:
            raise NotFoundError("Bank")
        return bank
