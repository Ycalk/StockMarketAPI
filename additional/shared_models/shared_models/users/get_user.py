from pydantic import BaseModel
from uuid import UUID


class GetUserRequest(BaseModel):
    id: UUID