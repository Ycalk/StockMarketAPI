from pydantic import BaseModel, field_validator
import re


class DeleteInstrumentRequest(BaseModel):
    ticker: str
    
    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        if not re.match(r'^[A-Z]{2,10}$', v):
            raise ValueError("Ticker must be uppercase and contain 2 to 10 characters.")
        return v


class DeleteInstrumentResponse(BaseModel):
    success: bool