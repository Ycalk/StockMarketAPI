from pydantic import BaseModel, field_validator
import re


class GetOrderbookRequest(BaseModel):
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


class OrderbookItem(BaseModel):
    price: int
    qty: int

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Price must be a positive integer.")
        return v

    @field_validator("qty")
    @classmethod
    def validate_qty(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be a positive integer.")
        return v


class GetOrderResponse(BaseModel):
    bid_levels: list[OrderbookItem]
    ask_levels: list[OrderbookItem]
