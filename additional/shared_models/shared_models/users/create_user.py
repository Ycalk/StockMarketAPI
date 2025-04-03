from pydantic import BaseModel
from .user import UserRole


class CreateUserRequest(BaseModel):
    name: str
    role: UserRole = UserRole.USER