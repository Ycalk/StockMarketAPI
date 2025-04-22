from pydantic import RootModel
from .instrument import Instrument


class GetInstrumentsResponse(RootModel):
    root: list[Instrument]
