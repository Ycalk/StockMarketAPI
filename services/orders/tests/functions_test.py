import pytest
from uuid import uuid4

from ..src.orders import Orders
from database import User, Instrument, Balance, Order
from shared_models.orders.requests.create_order import CreateOrderRequest
from shared_models.orders.models.orders_bodies import LimitOrderBody
from shared_models.orders.models.orders_bodies.direction import Direction
from shared_models.users.errors import UserNotFoundError, InsufficientFundsError
from shared_models.instruments.errors import InstrumentNotFoundError
from database.models.order import OrderType
from shared_models.orders.requests.create_order import CreateOrderResponse


@pytest.mark.asyncio
async def test_create_order_success_sell_limit(ctx: dict):
    user = await User.create(name="Test user")
    instrument = await Instrument.create(ticker="AAPL", name="Apple Inc.")
    await Balance.create(user=user, instrument=instrument, amount=100)

    body = LimitOrderBody(direction=Direction.SELL, ticker="AAPL", quantity=50, price=100)
    request = CreateOrderRequest(user_id=user.id, body=body)

    response: CreateOrderResponse = await Orders.create_order(ctx, request)

    assert isinstance(response, CreateOrderResponse)

    order = await Order.get(id=response.order_id).prefetch_related("instrument", "user")
    assert order.user.id == user.id
    assert order.instrument.ticker == instrument.ticker
    assert order.quantity == 50
    assert order.price == 100
    assert order.direction == Direction.SELL
    assert order.type == OrderType.LIMIT

@pytest.mark.asyncio
async def test_create_order_user_not_found(ctx: dict):
    await Instrument.create(ticker="AAPL", name="Apple Inc.")
    request = CreateOrderRequest(
        user_id=uuid4(),
        body=LimitOrderBody(direction=Direction.SELL, ticker="AAPL", quantity=10, price=100),
    )

    with pytest.raises(UserNotFoundError):
        await Orders.create_order(ctx, request)

@pytest.mark.asyncio
async def test_create_order_instrument_not_found(ctx: dict):
    user = await User.create(name="Test user")
    request = CreateOrderRequest(
        user_id=user.id,
        body=LimitOrderBody(direction=Direction.SELL, ticker="NOTEXIST", quantity=10, price=100),
    )

    with pytest.raises(InstrumentNotFoundError):
        await Orders.create_order(ctx, request)

@pytest.mark.asyncio
async def test_create_order_insufficient_funds(ctx: dict):
    user = await User.create(name="Test user")
    instrument = await Instrument.create(ticker="AAPL", name="Apple Inc.")
    await Balance.create(user=user, instrument=instrument, amount=5)

    request = CreateOrderRequest(
        user_id=user.id,
        body=LimitOrderBody(direction=Direction.SELL, ticker="AAPL", quantity=10, price=100),
    )

    with pytest.raises(InsufficientFundsError):
        await Orders.create_order(ctx, request)
