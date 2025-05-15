from uuid import UUID
from pydantic import RootModel
from ..models import MarketOrder, LimitOrder
from typing import Union


class ListOrdersRequest(RootModel):
    user_id: UUID


class ListOrdersResponse(RootModel):
    root: list[Union[MarketOrder, LimitOrder]]
