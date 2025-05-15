from pydantic import BaseModel
from uuid import UUID
from .order_status import OrderStatus
from .orders_bodies import MarketOrderBody
from datetime import datetime


class MarketOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    timestamp: datetime
    body: MarketOrderBody
