from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.ledger_entry import LedgerEntryType


class TransferRequest(BaseModel):
    from_account_id: UUID
    to_account_id: UUID
    amount_paise: int = Field(gt=0)


class TransferResponse(BaseModel):
    debit_entry_id: UUID
    credit_entry_id: UUID
    amount_paise: int


class LedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    entry_type: LedgerEntryType
    amount_paise: int
    balance_after_paise: int
    created_at: datetime


class BalanceResponse(BaseModel):
    account_id: UUID
    balance_paise: int
