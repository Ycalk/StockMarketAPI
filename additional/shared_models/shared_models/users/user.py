from pydantic import BaseModel, ConfigDict
from enum import Enum
from uuid import UUID

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

class User(BaseModel):
    id: UUID
    name: str
    role: UserRole

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore"
    )