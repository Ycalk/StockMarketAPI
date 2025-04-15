from fastapi import APIRouter
from microkit import MicroKitClient
from ..config import RedisConfig
from shared_models.instruments.add_instrument import AddInstrumentResponse
from shared_models.instruments import Instrument as InstrumentSharedModel
from shared_models.instruments.delete_instrument import DeleteInstrumentRequest, DeleteInstrumentResponse


router = APIRouter(prefix="/admin", tags=["admin"])
instruments_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Instruments")


@router.post("/instrument", response_model=AddInstrumentResponse)
async def create_instrument(request: InstrumentSharedModel):
    job = await instruments_client("add_instrument", request)
    if job is None:
        raise ValueError("Job is None")
    return await job.result()


@router.delete("/instrument/{ticker}", response_model=DeleteInstrumentResponse)
async def delete_instrument(ticker: str):
    job = await instruments_client("delete_instrument", DeleteInstrumentRequest(ticker=ticker))
    if job is None:
        raise ValueError("Job is None")
    return await job.result()