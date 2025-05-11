import pytest
from ..src.instruments import Instruments
from shared_models.instruments.add_instrument import AddInstrumentRequest
from shared_models.instruments.delete_instrument import DeleteInstrumentRequest
from shared_models.instruments.get_instruments import GetInstrumentsResponse
from shared_models.instruments import Instrument as InstrumentSharedModel
from shared_models.instruments.errors import (
    InstrumentAlreadyExistsError,
    InstrumentNotFoundError,
)
import asyncio


@pytest.mark.asyncio
async def test_instrument_lifecycle(ctx: dict):
    # 1. Check initial state (no instruments)
    response: GetInstrumentsResponse = await Instruments.get_instruments(ctx)
    assert len(response.root) == 0

    # 2. Adding a new instrument
    ticker = "AAPL"
    name = "Apple Inc."
    await Instruments.add_instrument(
        ctx,
        AddInstrumentRequest(
            instrument=InstrumentSharedModel(ticker=ticker, name=name)
        ),
    )

    # 3. Check that the instrument was added
    response = await Instruments.get_instruments(ctx)
    assert len(response.root) == 1
    assert response.root[0].ticker == ticker
    assert response.root[0].name == name

    # 4. Deleting the instrument
    await Instruments.delete_instrument(ctx, DeleteInstrumentRequest(ticker=ticker))

    # 5. Check that the instrument was deleted
    response = await Instruments.get_instruments(ctx)
    assert len(response.root) == 0


@pytest.mark.asyncio
async def test_add_duplicate_instrument(ctx: dict):
    ticker = "GOOGL"
    await Instruments.add_instrument(
        ctx,
        AddInstrumentRequest(
            instrument=InstrumentSharedModel(ticker=ticker, name="Alphabet Inc.")
        ),
    )

    with pytest.raises(InstrumentAlreadyExistsError):
        await Instruments.add_instrument(
            ctx,
            AddInstrumentRequest(
                instrument=InstrumentSharedModel(ticker=ticker, name="Google Inc.")
            ),
        )

    response: GetInstrumentsResponse = await Instruments.get_instruments(ctx)
    assert len(response.root) == 1
    assert response.root[0].name == "Alphabet Inc."


@pytest.mark.asyncio
async def test_get_instruments_after_multiple_operations(ctx: dict):
    # 1. Adding multiple instruments
    instruments_data = [
        ("TSLA", "Tesla"),
        ("AMZN", "Amazon"),
        ("META", "Meta Platforms"),
    ]

    for ticker, name in instruments_data:
        await Instruments.add_instrument(
            ctx,
            AddInstrumentRequest(
                instrument=InstrumentSharedModel(ticker=ticker, name=name)
            ),
        )

    # 2. Checking the list of instruments
    response: GetInstrumentsResponse = await Instruments.get_instruments(ctx)
    assert len(response.root) == 3

    # 3. Deleting one instrument
    await Instruments.delete_instrument(ctx, DeleteInstrumentRequest(ticker="AMZN"))

    # 4. Checking the list of instruments again
    new_response: GetInstrumentsResponse = await Instruments.get_instruments(ctx)
    assert len(new_response.root) == 2
    tickers = {i.ticker for i in new_response.root}
    assert "TSLA" in tickers
    assert "META" in tickers
    assert "AMZN" not in tickers


@pytest.mark.asyncio
async def test_concurrent_instrument_operations(ctx: dict):
    ticker = "CONC"
    name = "Concurrency Test"

    async def add_task():
        await Instruments.add_instrument(
            ctx,
            AddInstrumentRequest(
                instrument=InstrumentSharedModel(ticker=ticker, name=name)
            ),
        )

    async def delete_task():
        try:
            await Instruments.delete_instrument(
                ctx, DeleteInstrumentRequest(ticker=ticker)
            )
        except InstrumentNotFoundError:
            pass

    await asyncio.gather(add_task(), delete_task())

    response: GetInstrumentsResponse = await Instruments.get_instruments(ctx)
    assert len(response.root) in (0, 1)
    if len(response.root) == 1:
        assert response.root[0].ticker == ticker
