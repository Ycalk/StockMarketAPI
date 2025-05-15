from uuid import UUID
from pydantic import RootModel
from ..models import MarketOrder, LimitOrder
from typing import Union


class GetOrderRequest(RootModel):
    user_id: UUID
    order_id: UUID


class GetOrderResponse(RootModel):
    root: Union[MarketOrder, LimitOrder]
