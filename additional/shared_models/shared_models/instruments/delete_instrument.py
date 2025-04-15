from pydantic import BaseModel


class DeleteInstrumentRequest(BaseModel):
    ticker: str


class DeleteInstrumentResponse(BaseModel):
    success: bool