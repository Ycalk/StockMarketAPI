from uuid import UUID
from pydantic import BaseModel
from ..models.orders_bodies import MarketOrderBody, LimitOrderBody
from typing import Union


class CreateOrderRequest(BaseModel):
    body: Union[MarketOrderBody, LimitOrderBody]
    user_id: UUID


class CreateOrderResponse(BaseModel):
    order_id: UUID
