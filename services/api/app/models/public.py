from uuid import UUID
from pydantic import BaseModel, model_validator
from shared_models.users.user import UserRole
from ..services.token import generate_api_key

class RegisterUserRequest(BaseModel):
    name: str