from pydantic import BaseModel
from .instrument import Instrument


class GetInstrumentsResponse(BaseModel):
    __root__: list[Instrument]