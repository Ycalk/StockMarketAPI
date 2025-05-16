from datetime import datetime
from pydantic import BaseModel, field_validator, RootModel
import re


class GetTransactionsRequest(BaseModel):
    ticker: str
    limit: int = 10

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{2,10}$", v):
            raise ValueError("Ticker must be uppercase and contain 2 to 10 characters.")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Limit must be a positive integer.")
        return v


class Transaction(BaseModel):
    ticker: str
    amount: int
    price: int
    timestamp: datetime

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{2,10}$", v):
            raise ValueError("Ticker must be uppercase and contain 2 to 10 characters.")
        return v

    @field_validator("amount", "price")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Amount and price must be positive integers.")
        return v


class GetTransactionsResponse(RootModel):
    root: list[Transaction]
