from pydantic import BaseModel


class ResponseStatus(BaseModel):
    success: bool