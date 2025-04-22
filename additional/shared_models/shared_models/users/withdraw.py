from pydantic import BaseModel, field_validator
import re
from uuid import UUID


class WithdrawRequest(BaseModel):
    user_id: UUID
    ticker: str
    amount: int

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{2,10}$", v):
            raise ValueError("Ticker must be uppercase and contain 2 to 10 characters.")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount must be a positive integer.")
        return v
