from pydantic import BaseModel
from uuid import UUID


class DeleteUserRequest(BaseModel):
    id: UUID