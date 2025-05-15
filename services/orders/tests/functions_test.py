import pytest
from uuid import uuid4

from ..src.orders import Orders
from database import User, Instrument, Balance, Order
from shared_models.orders.requests.create_order import CreateOrderRequest
from shared_models.orders.models.orders_bodies import LimitOrderBody
from shared_models.orders.models.orders_bodies.direction import Direction
from shared_models.users.errors import UserNotFoundError, InsufficientFundsError
from shared_models.instruments.errors import InstrumentNotFoundError
from database.models.order import (
    OrderType as DatabaseOrderType,
    OrderStatus as DatabaseOrderStatus,
    Direction as DatabaseOrderDirection,
)
from shared_models.orders.requests.create_order import CreateOrderResponse
from shared_models.orders.requests.list_orders import (
    ListOrdersRequest,
    ListOrdersResponse,
)
from shared_models.orders.requests.get_order import GetOrderRequest, GetOrderResponse
from shared_models.orders.errors import OrderNotFoundError
from shared_models.orders.requests.cancel_order import CancelOrderRequest


@pytest.mark.asyncio
async def test_create_order_success_sell_limit(ctx: dict):
    user = await User.create(name="Test user")
    instrument = await Instrument.create(ticker="AAPL", name="Apple Inc.")
    await Balance.create(user=user, instrument=instrument, amount=100)

    body = LimitOrderBody(
        direction=Direction.SELL, ticker="AAPL", quantity=50, price=100
    )
    request = CreateOrderRequest(user_id=user.id, body=body)

    response: CreateOrderResponse = await Orders.create_order(ctx, request)

    assert isinstance(response, CreateOrderResponse)

    order = await Order.get(id=response.order_id).prefetch_related("instrument", "user")
    assert order.user.id == user.id
    assert order.instrument.ticker == instrument.ticker
    assert order.quantity == 50
    assert order.price == 100
    assert order.direction == Direction.SELL
    assert order.type == DatabaseOrderType.LIMIT


@pytest.mark.asyncio
async def test_create_order_user_not_found(ctx: dict):
    await Instrument.create(ticker="AAPL", name="Apple Inc.")
    request = CreateOrderRequest(
        user_id=uuid4(),
        body=LimitOrderBody(
            direction=Direction.SELL, ticker="AAPL", quantity=10, price=100
        ),
    )

    with pytest.raises(UserNotFoundError):
        await Orders.create_order(ctx, request)


@pytest.mark.asyncio
async def test_create_order_instrument_not_found(ctx: dict):
    user = await User.create(name="Test user")
    request = CreateOrderRequest(
        user_id=user.id,
        body=LimitOrderBody(
            direction=Direction.SELL, ticker="NOTEXIST", quantity=10, price=100
        ),
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
        body=LimitOrderBody(
            direction=Direction.SELL, ticker="AAPL", quantity=10, price=100
        ),
    )

    with pytest.raises(InsufficientFundsError):
        await Orders.create_order(ctx, request)


@pytest.mark.asyncio
async def test_list_orders_success(ctx: dict):
    user = await User.create(name="Test user")
    instrument = await Instrument.create(ticker="AAPL", name="Apple Inc.")
    await Order.create(
        user=user,
        type=DatabaseOrderType.LIMIT,
        direction=DatabaseOrderDirection.SELL,
        instrument=instrument,
        quantity=1,
        price=100,
    )
    await Order.create(
        user=user,
        type=DatabaseOrderType.LIMIT,
        direction=DatabaseOrderDirection.BUY,
        instrument=instrument,
        quantity=2,
        price=200,
    )

    request = ListOrdersRequest(user_id=user.id)
    response: ListOrdersResponse = await Orders.list_orders(ctx, request)

    assert isinstance(response, ListOrdersResponse)
    assert len(response.root) == 2
    for order in response.root:
        assert order.user_id == user.id


@pytest.mark.asyncio
async def test_list_orders_user_not_found(ctx: dict):
    request = ListOrdersRequest(user_id=uuid4())

    with pytest.raises(UserNotFoundError):
        await Orders.list_orders(ctx, request)


@pytest.mark.asyncio
async def test_get_order_success(ctx: dict):
    user = await User.create(name="Test user")
    instrument = await Instrument.create(ticker="AAPL", name="Apple Inc.")
    order = await Order.create(
        user=user,
        type=DatabaseOrderType.LIMIT,
        direction=DatabaseOrderDirection.BUY,
        instrument=instrument,
        quantity=2,
        price=200,
    )

    request = GetOrderRequest(user_id=user.id, order_id=order.id)
    response: GetOrderResponse = await Orders.get_order(ctx, request)

    assert isinstance(response, GetOrderResponse)
    assert response.root.id == order.id
    assert response.root.user_id == user.id


@pytest.mark.asyncio
async def test_get_order_not_found(ctx: dict):
    user = await User.create(name="Test user")
    request = GetOrderRequest(user_id=user.id, order_id=uuid4())

    with pytest.raises(OrderNotFoundError):
        await Orders.get_order(ctx, request)


@pytest.mark.asyncio
async def test_get_order_wrong_user(ctx: dict):
    user1 = await User.create(name="User 1")
    user2 = await User.create(name="User 2")
    instrument = await Instrument.create(ticker="AAPL", name="Apple Inc.")
    order = await Order.create(
        user=user1,
        type=DatabaseOrderType.LIMIT,
        direction=DatabaseOrderDirection.BUY,
        instrument=instrument,
        quantity=2,
        price=200,
    )

    request = GetOrderRequest(user_id=user2.id, order_id=order.id)

    with pytest.raises(OrderNotFoundError):
        await Orders.get_order(ctx, request)


@pytest.mark.asyncio
async def test_cancel_order_success(ctx: dict):
    user = await User.create(name="Test user")
    instrument = await Instrument.create(ticker="AAPL", name="Apple Inc.")
    order = await Order.create(
        user=user,
        type=DatabaseOrderType.LIMIT,
        direction=DatabaseOrderDirection.BUY,
        instrument=instrument,
        quantity=2,
        price=200,
    )

    request = CancelOrderRequest(user_id=user.id, order_id=order.id)
    await Orders.cancel_order(ctx, request)

    refreshed_order = await Order.get(id=order.id)
    assert refreshed_order.status == DatabaseOrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_order_not_found(ctx: dict):
    user = await User.create(name="Test user")
    request = CancelOrderRequest(user_id=user.id, order_id=uuid4())

    with pytest.raises(OrderNotFoundError):
        await Orders.cancel_order(ctx, request)


@pytest.mark.asyncio
async def test_cancel_order_wrong_user(ctx: dict):
    user1 = await User.create(name="User 1")
    user2 = await User.create(name="User 2")
    instrument = await Instrument.create(ticker="AAPL", name="Apple Inc.")
    order = await Order.create(
        user=user1,
        type=DatabaseOrderType.LIMIT,
        direction=DatabaseOrderDirection.BUY,
        instrument=instrument,
        quantity=2,
        price=200,
    )

    request = CancelOrderRequest(user_id=user2.id, order_id=order.id)

    with pytest.raises(OrderNotFoundError):
        await Orders.cancel_order(ctx, request)
