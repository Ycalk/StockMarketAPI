from uuid import UUID
from pydantic import BaseModel, model_validator
from shared_models.users.user import UserRole
from ..services.token import generate_api_key

class RegisterUserRequest(BaseModel):
    name: str

class RegisterUserResponse(BaseModel):
    id: UUID
    name: str
    role: UserRole
    api_key: str
    
    @model_validator(mode='before')
    def autofill_api_key(cls, data: dict):
        if 'api_key' not in data:
            data['api_key'] = generate_api_key(data['id'])
        return data