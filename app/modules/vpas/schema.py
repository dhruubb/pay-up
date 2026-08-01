import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

VPA_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9]+$")


class VpaCreateRequest(BaseModel):
    account_id: UUID
    psp_id: UUID
    address: str

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str) -> str:
        if not VPA_PATTERN.match(value):
            raise ValueError("VPA address must be in the form 'username@psphandle'")
        return value.lower()


class VpaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    psp_id: UUID
    address: str
    is_primary: bool


class VpaResolveResponse(BaseModel):
    address: str
    account_id: UUID
