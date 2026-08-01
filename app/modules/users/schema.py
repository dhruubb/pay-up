from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"