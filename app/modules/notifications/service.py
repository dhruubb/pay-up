from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schema import NotificationResponse


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    async def list_my_notifications(self, user_id: UUID) -> list[NotificationResponse]:
        notifications = await self.repo.list_for_user(user_id)
        return [NotificationResponse.model_validate(n) for n in notifications]
