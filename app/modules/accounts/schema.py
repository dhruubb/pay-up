from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.account import AccountStatus


class AccountCreateRequest(BaseModel):
    bank_id: UUID


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bank_id: UUID
    account_number: str
    status: AccountStatus
