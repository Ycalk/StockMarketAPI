from pydantic import BaseModel
from .user import UserRole, User


class CreateUserRequest(BaseModel):
    name: str
    role: UserRole = UserRole.USER
    

class CreateUserResponse(BaseModel):
    user: User
    