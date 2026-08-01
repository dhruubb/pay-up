from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.psps.schema import PspCreateRequest, PspResponse
from app.modules.psps.service import PspService

router = APIRouter(prefix="/psps", tags=["PSPs"])


@router.post(
    "",
    response_model=PspResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_psp(
    request: PspCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PspService(db)
    psp = await service.create_psp(request)
    return PspResponse.model_validate(psp)


@router.get(
    "",
    response_model=list[PspResponse],
)
async def list_psps(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PspService(db)
    psps = await service.list_psps()
    return [PspResponse.model_validate(psp) for psp in psps]


@router.get(
    "/{psp_id}",
    response_model=PspResponse,
)
async def get_psp(
    psp_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PspService(db)
    psp = await service.get_psp(psp_id)
    return PspResponse.model_validate(psp)
