from pydantic import BaseModel


class RegisterUserRequest(BaseModel):
    name: str