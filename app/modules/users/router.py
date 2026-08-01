from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.modules.users.schema import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.register(request)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    request: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    return await service.login(request)


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)