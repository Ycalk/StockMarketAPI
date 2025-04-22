from pydantic import BaseModel
from .instrument import Instrument


class AddInstrumentRequest(BaseModel):
    instrument: Instrument
