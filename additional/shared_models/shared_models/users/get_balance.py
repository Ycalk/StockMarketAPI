from typing import Dict
from pydantic import BaseModel, RootModel
from uuid import UUID


class GetBalanceRequest(BaseModel):
    user_id: UUID


class GetBalanceResponse(RootModel):
    root: Dict[str, int]