from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.audit.schema import AuditLogResponse
from app.modules.audit.service import AuditLogService

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get(
    "",
    response_model=list[AuditLogResponse],
)
async def list_my_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AuditLogService(db)
    return await service.list_my_logs(current_user.id)
