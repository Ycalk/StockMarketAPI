from pydantic import BaseModel
from uuid import UUID
from .user import User


class GetUserRequest(BaseModel):
    id: UUID


class GetUserResponse(BaseModel):
    user: User
