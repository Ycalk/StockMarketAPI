from typing import Union
from pydantic import BaseModel, field_validator, RootModel
from ..models.orders_bodies import LimitOrderBody, MarketOrderBody
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


class GetTransactionsResponse(RootModel):
    root: list[Union[LimitOrderBody, MarketOrderBody]]
