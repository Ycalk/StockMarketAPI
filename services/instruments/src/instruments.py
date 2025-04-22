import logging
from tortoise import Tortoise
from tortoise.transactions import in_transaction
from database.config import TORTOISE_ORM
from microkit.service import Service, service_method
from arq.connections import ArqRedis
from shared_models.instruments.get_instruments import GetInstrumentsResponse
from shared_models.instruments.add_instrument import AddInstrumentRequest
from shared_models.instruments.delete_instrument import DeleteInstrumentRequest
from shared_models.instruments.errors import (
    CriticalError,
    InstrumentAlreadyExistsError,
    InstrumentNotFoundError,
)
from tortoise.exceptions import IntegrityError
from database import Instrument


class Instruments(Service):
    async def init(self):
        self.logger = logging.getLogger("users")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        self.logger.info("Database connection initialized.")

    # Methods
    @service_method
    async def get_instruments(
        self: "Instruments", redis: ArqRedis
    ) -> GetInstrumentsResponse:
        try:
            instruments = await Instrument.all()
            return GetInstrumentsResponse.model_validate(instruments)
        except Exception as e:
            msg = f"Error fetching instruments: {e}"
            self.logger.critical(msg)
            raise CriticalError(msg)

    @service_method
    async def add_instrument(
        self: "Instruments", redis: ArqRedis, request: AddInstrumentRequest
    ) -> None:
        try:
            instrument = await Instrument.create(
                **request.instrument.model_dump(exclude_unset=True)
            )
        except IntegrityError:
            raise InstrumentAlreadyExistsError(request.instrument.ticker)
        except Exception as e:
            msg = f"Error creating instrument: {e}"
            self.logger.critical(msg)
            raise CriticalError(msg)
        self.logger.info(f"Instrument created with ticker: {instrument.ticker}")

    @service_method
    async def delete_instrument(
        self: "Instruments", redis: ArqRedis, request: DeleteInstrumentRequest
    ) -> None:
        async with in_transaction() as conn:
            try:
                instrument = (
                    await Instrument.filter(ticker=request.ticker)
                    .select_for_update()
                    .using_db(conn)
                    .first()
                )
                if not instrument:
                    raise InstrumentNotFoundError(request.ticker)
                await instrument.delete(using_db=conn)
            except InstrumentNotFoundError as ve:
                self.logger.error(f"Validation error in delete_instrument: {ve}")
                raise
            except Exception as e:
                msg = f"Error deleting instrument: {e}"
                self.logger.critical(msg)
                raise CriticalError(msg)
        self.logger.info(f"Instrument with ticker {request.ticker} deleted.")
