from pydantic import BaseModel, ConfigDict, field_validator
import re


class Instrument(BaseModel):
    ticker: str
    name: str

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{2,10}$", v):
            raise ValueError("Ticker must be uppercase and contain 2 to 10 characters.")
        return v
