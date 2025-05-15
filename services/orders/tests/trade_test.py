import pytest
from ..src.orders import Orders
from database import Instrument, User, Balance
from typing import Union
from shared_models.orders.models import LimitOrder, MarketOrder
from shared_models.orders.requests.create_order import CreateOrderRequest
from shared_models.orders.models.orders_bodies import LimitOrderBody
from shared_models.orders.models.orders_bodies.direction import (
    Direction as SharedModelOrderDirection,
)
from shared_models.orders.models.order_status import OrderStatus
from shared_models.orders.requests.get_order import GetOrderRequest


@pytest.mark.asyncio
async def test_limit_buy_order_trading_partial_fill(
    ctx: dict, instrument: Instrument, rub: Instrument
):
    seller_rub_amount = 0
    buyer_rub_amount = 1000

    seller_instrument_amount = 10
    buyer_instrument_amount = 0

    seller = await User.create(name="Seller")
    buyer = await User.create(name="Buyer")

    await Balance.create(
        user=seller, instrument=instrument, amount=seller_instrument_amount
    )
    await Balance.create(user=buyer, instrument=rub, amount=buyer_rub_amount)
    request1 = CreateOrderRequest(
        user_id=buyer.id,
        body=LimitOrderBody(
            direction=SharedModelOrderDirection.BUY,
            ticker=instrument.ticker,
            quantity=10,
            price=100,
        ),
    )

    request2 = CreateOrderRequest(
        user_id=seller.id,
        body=LimitOrderBody(
            direction=SharedModelOrderDirection.SELL,
            ticker=instrument.ticker,
            quantity=5,
            price=100,
        ),
    )

    buy_order_id = (await Orders.create_order(ctx, request1)).order_id
    sell_order_id = (await Orders.create_order(ctx, request2)).order_id

    buy_order: Union[MarketOrder, LimitOrder] = (
        await Orders.get_order(
            ctx, GetOrderRequest(user_id=buyer.id, order_id=buy_order_id)
        )
    ).root
    sell_order: Union[MarketOrder, LimitOrder] = (
        await Orders.get_order(
            ctx, GetOrderRequest(user_id=seller.id, order_id=sell_order_id)
        )
    ).root

    seller_rub_balance = await Balance.get(user=seller, instrument=rub)
    buyer_rub_balance = await Balance.get(user=buyer, instrument=rub)

    seller_instrument_balance = await Balance.get(user=seller, instrument=instrument)
    buyer_instrument_balance = await Balance.get(user=buyer, instrument=instrument)

    transaction_amount = 5
    transaction_price = 100

    assert isinstance(buy_order, LimitOrder)
    assert isinstance(sell_order, LimitOrder)
    assert buy_order.filled == transaction_amount
    assert sell_order.filled == transaction_amount
    assert sell_order.status == OrderStatus.EXECUTED
    assert buy_order.status == OrderStatus.NEW

    assert (
        seller_rub_balance.amount
        == seller_rub_amount + transaction_amount * transaction_price
    )
    assert (
        buyer_rub_balance.amount
        == buyer_rub_amount - transaction_amount * transaction_price
    )

    assert (
        seller_instrument_balance.amount
        == seller_instrument_amount - transaction_amount
    )
    assert (
        buyer_instrument_balance.amount == buyer_instrument_amount + transaction_amount
    )


@pytest.mark.asyncio
async def test_limit_buy_order_trading_with_yourself_partial_fill(
    ctx: dict, instrument: Instrument, user: User, rub: Instrument
):
    instrument_init_balance = 10
    rub_init_balance = 1000
    await Balance.create(
        user=user, instrument=instrument, amount=instrument_init_balance
    )
    await Balance.create(user=user, instrument=rub, amount=rub_init_balance)
    request1 = CreateOrderRequest(
        user_id=user.id,
        body=LimitOrderBody(
            direction=SharedModelOrderDirection.BUY,
            ticker=instrument.ticker,
            quantity=10,
            price=100,
        ),
    )

    request2 = CreateOrderRequest(
        user_id=user.id,
        body=LimitOrderBody(
            direction=SharedModelOrderDirection.SELL,
            ticker=instrument.ticker,
            quantity=5,
            price=100,
        ),
    )

    buy_order_id = (await Orders.create_order(ctx, request1)).order_id
    sell_order_id = (await Orders.create_order(ctx, request2)).order_id

    buy_order: Union[MarketOrder, LimitOrder] = (
        await Orders.get_order(
            ctx, GetOrderRequest(user_id=user.id, order_id=buy_order_id)
        )
    ).root
    sell_order: Union[MarketOrder, LimitOrder] = (
        await Orders.get_order(
            ctx, GetOrderRequest(user_id=user.id, order_id=sell_order_id)
        )
    ).root

    instrument_balance, _ = await Balance.get_or_create(
        user=user, instrument=instrument
    )
    rub_balance, _ = await Balance.get_or_create(user=user, instrument=rub)

    assert isinstance(buy_order, LimitOrder)
    assert isinstance(sell_order, LimitOrder)
    assert buy_order.filled == 5
    assert sell_order.filled == 5
    assert sell_order.status == OrderStatus.EXECUTED
    assert buy_order.status == OrderStatus.NEW

    # Trading with yourself => balance does not change
    assert instrument_balance.amount == instrument_init_balance
    assert rub_balance.amount == rub_init_balance
