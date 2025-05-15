from uuid import UUID
from pydantic import BaseModel


class CancelOrderRequest(BaseModel):
    user_id: UUID
    order_id: UUID
