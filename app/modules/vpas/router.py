from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.vpas.schema import VpaCreateRequest, VpaResolveResponse, VpaResponse
from app.modules.vpas.service import VpaService

router = APIRouter(prefix="/vpas", tags=["VPAs"])


@router.post(
    "",
    response_model=VpaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vpa(
    request: VpaCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VpaService(db)
    vpa = await service.create_vpa(current_user.id, request)
    return VpaResponse.model_validate(vpa)


@router.get(
    "",
    response_model=list[VpaResponse],
)
async def list_my_vpas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VpaService(db)
    vpas = await service.list_my_vpas(current_user.id)
    return [VpaResponse.model_validate(vpa) for vpa in vpas]


@router.get(
    "/resolve/{address}",
    response_model=VpaResolveResponse,
)
async def resolve_vpa(
    address: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VpaService(db)
    vpa = await service.resolve(address)
    return VpaResolveResponse(address=vpa.address, account_id=vpa.account_id)


@router.get(
    "/{vpa_id}",
    response_model=VpaResponse,
)
async def get_vpa(
    vpa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VpaService(db)
    vpa = await service.get_vpa(current_user.id, vpa_id)
    return VpaResponse.model_validate(vpa)


@router.patch(
    "/{vpa_id}/primary",
    response_model=VpaResponse,
)
async def set_primary_vpa(
    vpa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VpaService(db)
    vpa = await service.set_primary(current_user.id, vpa_id)
    return VpaResponse.model_validate(vpa)
