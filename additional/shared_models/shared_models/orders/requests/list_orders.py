from uuid import UUID
from pydantic import RootModel, BaseModel
from ..models import MarketOrder, LimitOrder
from typing import Union


class ListOrdersRequest(BaseModel):
    user_id: UUID


class ListOrdersResponse(RootModel):
    root: list[Union[MarketOrder, LimitOrder]]
