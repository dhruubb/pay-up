from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PspCreateRequest(BaseModel):
    name: str
    code: str


class PspResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
