from pydantic import BaseModel
from enum import Enum
from uuid import UUID

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class User(BaseModel):
    id: UUID
    name: str
    role: UserRole

    class Config:
        from_attributes = True