import re
from pydantic import BaseModel, field_validator
from .direction import Direction


class MarketOrderBody(BaseModel):
    direction: Direction
    ticker: str
    quantity: int

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{2,10}$", v):
            raise ValueError("Ticker must be uppercase and contain 2 to 10 characters.")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be a positive integer.")
        return v
