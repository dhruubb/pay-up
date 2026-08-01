from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.notifications.schema import NotificationResponse
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
)
async def list_my_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NotificationService(db)
    return await service.list_my_notifications(current_user.id)
