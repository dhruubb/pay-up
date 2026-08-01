from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateError, NotFoundError
from app.models.psp import Psp
from app.modules.psps.repository import PspRepository
from app.modules.psps.schema import PspCreateRequest


class PspService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PspRepository(db)

    async def create_psp(self, request: PspCreateRequest) -> Psp:
        existing = await self.repo.get_by_code(request.code)
        if existing:
            raise DuplicateError("PSP", "code")

        psp = Psp(name=request.name, code=request.code)
        psp = await self.repo.create(psp)
        await self.db.commit()
        return psp

    async def list_psps(self) -> list[Psp]:
        return await self.repo.list_all()

    async def get_psp(self, psp_id: UUID) -> Psp:
        psp = await self.repo.get_by_id(psp_id)
        if not psp:
            raise NotFoundError("PSP")
        return psp
