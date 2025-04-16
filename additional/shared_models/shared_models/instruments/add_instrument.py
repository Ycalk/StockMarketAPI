from pydantic import BaseModel


class AddInstrumentResponse(BaseModel):
    success: bool