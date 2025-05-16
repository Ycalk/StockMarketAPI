from pydantic import BaseModel, field_validator
from uuid import UUID
from .order_status import OrderStatus
from .orders_bodies import LimitOrderBody
from datetime import datetime


class LimitOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    timestamp: datetime
    body: LimitOrderBody
    filled: int

    @field_validator("filled")
    @classmethod
    def validate_filled(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Filled quantity must be non-negative.")
        return v
