import logging
from tortoise import Tortoise
from database.config import TORTOISE_ORM
from microkit.service import Service, service_method
from arq.connections import ArqRedis
from shared_models.instruments.get_instruments import GetInstrumentsResponse
from shared_models.instruments.add_instrument import AddInstrumentResponse
from shared_models.instruments.delete_instrument import DeleteInstrumentRequest, DeleteInstrumentResponse
from shared_models.instruments import Instrument as InstrumentSharedModel
from database import Instrument


class Instruments(Service):
    async def init(self):
        self.logger = logging.getLogger("users")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        self.logger.info("Database connection initialized.")
    
    # Methods
    @service_method
    async def get_instruments(self: "Instruments", redis: ArqRedis) -> GetInstrumentsResponse:
        instruments = await Instrument.all()
        return GetInstrumentsResponse.model_validate(instruments)
    
    @service_method
    async def add_instrument(self: "Instruments", redis: ArqRedis, request: InstrumentSharedModel) -> AddInstrumentResponse:
        try:
            instrument = await Instrument.create(**request.model_dump(exclude_unset=True))
            self.logger.info(f"Instrument created with ticker: {instrument.ticker}")
            return AddInstrumentResponse(success=True)
        except Exception as e:
            self.logger.error(f"Error creating instrument: {e}")
            return AddInstrumentResponse(success=False)
    
    @service_method
    async def delete_instrument(self: "Instruments", redis: ArqRedis, ticker: DeleteInstrumentRequest) -> DeleteInstrumentResponse:
        try:
            instrument = await Instrument.get(ticker=ticker.ticker)
            await instrument.delete()
            self.logger.info(f"Instrument deleted with ticker: {ticker.ticker}")
            return DeleteInstrumentResponse(success=True)
        except Exception as e:
            self.logger.error(f"Error deleting instrument: {e}")
            return DeleteInstrumentResponse(success=False)