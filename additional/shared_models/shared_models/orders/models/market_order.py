from pydantic import BaseModel
from uuid import UUID
from .order_status import OrderStatus
from .order_bodies import LimitOrderBody
from datetime import datetime


class LimitOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    timestamp: datetime
    body: LimitOrderBody