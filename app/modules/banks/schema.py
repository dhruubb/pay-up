from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BankCreateRequest(BaseModel):
    name: str
    code: str


class BankResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
