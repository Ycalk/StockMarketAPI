from pydantic import BaseModel
from .instrument import Instrument


class GetInstrumentsResponse(BaseModel):
    __pydantic_root_model__: list[Instrument]