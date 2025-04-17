from pydantic import BaseModel
from uuid import UUID
from .user import User


class DeleteUserRequest(BaseModel):
    id: UUID


class DeleteUserResponse(BaseModel):
    user: User
