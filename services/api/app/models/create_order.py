from uuid import UUID
from pydantic import BaseModel
from typing import Optional


class CreateOrderResponse(BaseModel):
    success: bool
    order_id: Optional[UUID]
