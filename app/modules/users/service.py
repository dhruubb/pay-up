from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, DuplicateError, NotFoundError
from app.core.jwt import create_access_token
from app.core.security import hash_password, verify_password
from app.models.audit_log import AuditActorType
from app.models.user import User
from app.modules.audit.service import AuditLogService
from app.modules.users.repository import UserRepository
from app.modules.users.schema import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)
        self.audit_service = AuditLogService(db)

    async def register(self, request: UserRegisterRequest) -> User:
        existing = await self.repo.get_by_email(request.email)
        if existing:
            raise DuplicateError("User", "email")

        user = User(
            name=request.name,
            email=request.email,
            phone=request.phone,
            password_hash=hash_password(request.password),
        )

        user = await self.repo.create(user)
        await self.audit_service.log(
            actor_type=AuditActorType.USER,
            actor_id=user.id,
            action="USER_REGISTERED",
            resource_type="User",
            resource_id=user.id,
            details={"email": user.email},
        )
        await self.db.commit()
        return user

    async def login(self, request: UserLoginRequest) -> TokenResponse:
        user = await self.repo.get_by_email(request.email)

        if not user or not verify_password(request.password, user.password_hash):
            await self.audit_service.log(
                actor_type=AuditActorType.USER if user else AuditActorType.SYSTEM,
                actor_id=user.id if user else None,
                action="LOGIN_FAILED",
                resource_type="User",
                resource_id=user.id if user else None,
                details={"email": request.email},
            )
            await self.db.commit()
            raise AuthenticationError()

        token = create_access_token(user.id)
        await self.audit_service.log(
            actor_type=AuditActorType.USER,
            actor_id=user.id,
            action="LOGIN_SUCCESS",
            resource_type="User",
            resource_id=user.id,
            details={"email": user.email},
        )
        await self.db.commit()
        return TokenResponse(access_token=token)

    async def get_user_by_id(self, user_id) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User")
        return user

