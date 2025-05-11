import pytest
from ..src.instruments import Instruments
from shared_models.instruments.add_instrument import AddInstrumentRequest
from shared_models.instruments import Instrument as InstrumentSharedModel
from shared_models.instruments.delete_instrument import DeleteInstrumentRequest
from shared_models.instruments.get_instruments import GetInstrumentsResponse
from shared_models.instruments.errors import (
    InstrumentAlreadyExistsError,
    InstrumentNotFoundError,
)
from database import Instrument


@pytest.mark.asyncio
async def test_create_instrument(ctx: dict):
    await Instruments.add_instrument(
        ctx,
        AddInstrumentRequest(
            instrument=InstrumentSharedModel(ticker="ABC", name="Test Instrument")
        ),
    )

    instrument = await Instrument.get_or_none(ticker="ABC")
    assert instrument is not None
    assert instrument.ticker == "ABC"
    assert instrument.name == "Test Instrument"


@pytest.mark.asyncio
async def test_delete_instrument(ctx: dict):
    await Instrument.create(ticker="ABC", name="Test Instrument")

    await Instruments.delete_instrument(ctx, DeleteInstrumentRequest(ticker="ABC"))

    instrument = await Instrument.get_or_none(ticker="ABC")
    assert instrument is None


@pytest.mark.asyncio
async def test_get_instruments(ctx: dict):
    await Instrument.create(ticker="ABC", name="Test Instrument")

    response: GetInstrumentsResponse = await Instruments.get_instruments(ctx)
    assert isinstance(response, GetInstrumentsResponse)
    assert len(response.root) == 1
    assert response.root[0].ticker == "ABC"
    assert response.root[0].name == "Test Instrument"


@pytest.mark.asyncio
async def test_delete_nonexistent_instrument(ctx: dict):
    with pytest.raises(InstrumentNotFoundError):
        request = DeleteInstrumentRequest(ticker="XYZ")
        await Instruments.delete_instrument(ctx, request)


@pytest.mark.asyncio
async def test_create_existing_instrument(ctx: dict):
    await Instrument.create(ticker="ABC", name="Test Instrument")
    with pytest.raises(InstrumentAlreadyExistsError):
        request = AddInstrumentRequest(
            instrument=InstrumentSharedModel(
                ticker="ABC", name="Another test Instrument"
            )
        )
        await Instruments.add_instrument(ctx, request)
