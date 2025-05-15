from uuid import UUID
from pydantic import RootModel


class CancelOrderRequest(RootModel):
    user_id: UUID
    order_id: UUID
