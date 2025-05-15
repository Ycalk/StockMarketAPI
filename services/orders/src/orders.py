from typing import Optional, Union
from arq import ArqRedis
from microkit.service import Service, service_method
from database.config import TORTOISE_ORM
from tortoise.transactions import in_transaction
from tortoise.backends.base.client import TransactionContext
from database import Order, Balance, Instrument, User, Transaction
from tortoise import Tortoise
import logging
from database.models.order import (
    OrderStatus as DatabaseOrderStatus,
    Direction as DatabaseOrderDirection,
    OrderType as DatabaseOrderType,
)
from shared_models.instruments.errors import InstrumentNotFoundError
from shared_models.users.errors import UserNotFoundError, InsufficientFundsError
from shared_models.orders.models.orders_bodies import LimitOrderBody, MarketOrderBody
from shared_models.orders.models.order_status import (
    OrderStatus as SharedModelOrderStatus,
)
from shared_models.orders.models.orders_bodies.direction import (
    Direction as SharedModelOrderDirection,
)
from shared_models.orders.models import LimitOrder, MarketOrder
from shared_models.orders.errors import CriticalError, OrderNotFoundError
from shared_models.orders.requests.create_order import (
    CreateOrderRequest,
    CreateOrderResponse,
)
from shared_models.orders.models.orders_bodies.direction import Direction
from shared_models.orders.requests.list_orders import (
    ListOrdersRequest,
    ListOrdersResponse,
)
from shared_models.orders.requests.get_order import (
    GetOrderRequest,
    GetOrderResponse,
)
from shared_models.orders.requests.cancel_order import CancelOrderRequest


class Orders(Service):
    async def init(self):
        self.logger = logging.getLogger("users")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        self.logger.info("Database connection initialized.")

    async def execute_transaction(
        self, transaction: Transaction, context: TransactionContext
    ) -> None:
        if not transaction.buyer_order or not transaction.seller_order:
            raise CriticalError("Buyer or seller order not found")
        buyer = transaction.buyer_order.user if transaction.buyer_order else None
        seller = transaction.seller_order.user if transaction.seller_order else None
        if not buyer or not seller:
            raise CriticalError("Buyer or seller not found")

        # change orders filled amounts and statuses
        transaction.buyer_order.filled += transaction.quantity
        transaction.seller_order.filled += transaction.quantity
        if transaction.buyer_order.quantity == transaction.buyer_order.filled:
            transaction.buyer_order.status = DatabaseOrderStatus.EXECUTED
        if transaction.seller_order.quantity == transaction.seller_order.filled:
            transaction.seller_order.status = DatabaseOrderStatus.EXECUTED

        # move transaction.instrument from seller to buyer
        buyer_balance, _ = await Balance.get_or_create(
            user=buyer,
            ticker=transaction.instrument.ticker,
            using_db=context,  # type: ignore
        )
        seller_balance = await Balance.get_or_none(
            user=seller,
            ticker=transaction.instrument.ticker,
            using_db=context,  # type: ignore
        )
        if seller_balance is None or seller_balance.amount < transaction.quantity:
            raise CriticalError(
                f"Seller does not have enough {transaction.instrument.ticker} to create transaction"
            )
        buyer_balance.amount += transaction.quantity
        seller_balance.amount -= transaction.quantity

        # move rubs from buyer to seller
        buyer_rub_balance = await Balance.get_or_none(
            user=buyer,
            ticker="RUB",
            using_db=context,  # type: ignore
        )
        seller_rub_balance, _ = await Balance.get_or_create(
            user=seller,
            ticker="RUB",
            using_db=context,  # type: ignore
        )
        if buyer_rub_balance is None or buyer_rub_balance.amount < transaction.quantity:
            raise CriticalError("Buyer does not have enough RUB to create transaction")
        buyer_rub_balance.amount -= transaction.quantity
        seller_rub_balance.amount += transaction.quantity

        # save changes
        await buyer_balance.save(using_db=context)  # type: ignore
        await seller_balance.save(using_db=context)  # type: ignore
        await buyer_rub_balance.save(using_db=context)  # type: ignore
        await seller_rub_balance.save(using_db=context)  # type: ignore
        await transaction.save(using_db=context)  # type: ignore
        await transaction.buyer_order.save(using_db=context)  # type: ignore
        await transaction.seller_order.save(using_db=context)  # type: ignore

    async def create_transaction(
        self, order1: Order, order2: Order, context: TransactionContext
    ) -> Optional[Transaction]:
        if (
            order1.direction == order2.direction
            or order1.status != DatabaseOrderStatus.NEW
            or order2.status != DatabaseOrderStatus.NEW
        ):
            return None

        if order1.direction == DatabaseOrderDirection.BUY:
            buy_order = order1
            sell_order = order2
        else:
            sell_order = order1
            buy_order = order2

        def get_price() -> Optional[int]:
            if (sell_order.type == DatabaseOrderType.MARKET) ^ (
                buy_order.type == DatabaseOrderType.MARKET
            ):
                # if one of orders - market -> return limit order price
                if sell_order.type == DatabaseOrderType.LIMIT:
                    return sell_order.price
                else:
                    return buy_order.price

            elif (
                sell_order.type == DatabaseOrderType.LIMIT
                and buy_order.type == DatabaseOrderType.LIMIT
            ):
                if sell_order.price > buy_order.price:
                    return None

                # if both orders are limit orders, return order price with earlier creation date
                return (
                    sell_order.price
                    if sell_order.created_at < buy_order.created_at
                    else buy_order.price
                )
            else:
                # both orders are market orders -> cannot create transaction
                return None

        price = get_price()
        buyer_balance = await Balance.get_or_none(
            user=buy_order.user,
            ticker="RUB",
            using_db=context,  # type: ignore
        )

        if not buyer_balance or not price:
            return None

        quantity = min(
            buy_order.quantity - buy_order.filled,
            sell_order.quantity - sell_order.filled,
            buyer_balance.amount // price,
        )
        if quantity == 0:
            return None

        return Transaction(
            instrument=sell_order.instrument,
            price=price,
            buyer_order=buy_order,
            seller_order=sell_order,
            quantity=quantity,
        )

    async def execute_market_orders(
        self,
        market_orders: list[Order],
        buy_orders: list[Order],
        sell_orders: list[Order],
        context: TransactionContext,
    ) -> None:
        for market_order in market_orders:
            orders = (
                sell_orders
                if market_order.direction == DatabaseOrderDirection.BUY
                else buy_orders
            )
            for order in orders:
                transaction = await self.create_transaction(
                    market_order, order, context
                )
                if transaction:
                    await self.execute_transaction(transaction, context)
                else:
                    break
            if market_order.status != DatabaseOrderStatus.EXECUTED:
                market_order.status = DatabaseOrderStatus.PARTIALLY_EXECUTED
                await market_order.save(using_db=context)  # type: ignore

    async def execute_limit_orders(
        self,
        buy_orders: list[Order],
        sell_orders: list[Order],
        context: TransactionContext,
    ) -> None:
        for buy_order in buy_orders:
            for sell_order in sell_orders:
                transaction = await self.create_transaction(
                    buy_order, sell_order, context
                )
                if transaction:
                    await self.execute_transaction(transaction, context)
                else:
                    break
            if buy_order.status != DatabaseOrderStatus.EXECUTED:
                break

    async def execute_orders(self, ticker: str) -> None:
        async with in_transaction() as conn:
            instrument = await Instrument.get_or_none(ticker=ticker, using_db=conn)
            if not instrument:
                self.logger.warning(f"Instrument not found: {ticker}")
                return
            market_orders = (
                await Order.filter(
                    instrument=instrument,
                    type=DatabaseOrderType.MARKET,
                    status=DatabaseOrderStatus.NEW,
                )
                .using_db(conn)
                .all()
            )

            buy_orders = (
                await Order.filter(
                    instrument=instrument,
                    direction=DatabaseOrderDirection.BUY,
                    type=DatabaseOrderType.LIMIT,
                    status=DatabaseOrderStatus.NEW,
                )
                .using_db(conn)  # type: ignore
                .order_by("-price")
                .all()
            )

            sell_orders = (
                await Order.filter(
                    instrument=instrument,
                    direction=DatabaseOrderDirection.SELL,
                    type=DatabaseOrderType.LIMIT,
                    status=DatabaseOrderStatus.NEW,
                )
                .using_db(conn)  # type: ignore
                .order_by("price")
                .all()
            )

            await self.execute_market_orders(
                market_orders=market_orders,
                buy_orders=buy_orders,
                sell_orders=sell_orders,
                context=conn,
            )

            await self.execute_limit_orders(
                buy_orders=buy_orders, sell_orders=sell_orders, context=conn
            )

    async def get_lock_balance(
        self, user: User, instrument: Instrument, context: TransactionContext
    ) -> int:
        user_orders = await (
            Order.filter(
                user=user,
                instrument=instrument,
                status=DatabaseOrderStatus.NEW,
                direction=DatabaseOrderDirection.SELL,
            )
            .using_db(context)  # type: ignore
            .all()
        )
        return sum(order.quantity - order.filled for order in user_orders)

    def convert_database_model(
        self, database_model: Order
    ) -> Union[MarketOrder, LimitOrder]:
        if database_model.type == DatabaseOrderType.MARKET:
            return MarketOrder(
                id=database_model.id,
                status=SharedModelOrderStatus(database_model.status.value),
                user_id=database_model.user.id,
                timestamp=database_model.created_at,
                body=MarketOrderBody(
                    direction=SharedModelOrderDirection(database_model.direction.value),
                    ticker=database_model.instrument.ticker,
                    quantity=database_model.quantity,
                ),
            )
        else:
            return LimitOrder(
                id=database_model.id,
                status=SharedModelOrderStatus(database_model.status.value),
                user_id=database_model.user.id,
                timestamp=database_model.created_at,
                body=LimitOrderBody(
                    direction=SharedModelOrderDirection(database_model.direction.value),
                    ticker=database_model.instrument.ticker,
                    quantity=database_model.quantity,
                    price=database_model.price,
                ),
                filled=database_model.filled,
            )

    @service_method
    async def create_order(
        self: "Orders", redis: "ArqRedis", request: CreateOrderRequest
    ) -> CreateOrderResponse:
        async with in_transaction() as conn:
            try:
                instrument = await Instrument.get_or_none(
                    ticker=request.body.ticker, using_db=conn
                )
                if not instrument:
                    raise InstrumentNotFoundError(request.body.ticker)
                user = await User.get_or_none(id=request.user_id, using_db=conn)
                if not user:
                    raise UserNotFoundError(str(request.user_id))

                balance = await Balance.filter(user=user, instrument=instrument).first()

                if request.body.direction == Direction.SELL:
                    if balance is None:
                        raise InsufficientFundsError(
                            str(user.id), request.body.quantity, 0
                        )
                    maximum_to_sell = (
                        balance.amount
                        - await self.get_lock_balance(user, instrument, conn)
                        if balance
                        else 0
                    )
                    if maximum_to_sell < request.body.quantity:
                        raise InsufficientFundsError(
                            str(user.id), request.body.quantity, maximum_to_sell
                        )

                order_data = {
                    "user": user,
                    "type": DatabaseOrderType.LIMIT
                    if isinstance(request.body, LimitOrderBody)
                    else DatabaseOrderType.MARKET,
                    "direction": DatabaseOrderDirection.SELL
                    if request.body.direction == Direction.SELL
                    else DatabaseOrderDirection.BUY,
                    "instrument": instrument,
                    "quantity": request.body.quantity,
                }

                if isinstance(request.body, LimitOrderBody):
                    order_data["price"] = request.body.price
                order = await Order.create(using_db=conn, **order_data)
                return CreateOrderResponse(order_id=order.id)
            except (
                UserNotFoundError,
                InstrumentNotFoundError,
                InsufficientFundsError,
            ) as ve:
                self.logger.error(f"Validation error: {ve}")
                raise
            except Exception as e:
                self.logger.info(f"Unexpected error: {e}")
                raise CriticalError(f"Unexpected error: {e}")
            finally:
                lock = redis.lock(f"lock:orders:{request.body.ticker}", timeout=5)
                async with lock:
                    await self.execute_orders(request.body.ticker)

    @service_method
    async def list_orders(
        self: "Orders", redis: "ArqRedis", request: ListOrdersRequest
    ) -> ListOrdersResponse:
        async with in_transaction() as conn:
            try:
                user = await User.get_or_none(id=request.user_id, using_db=conn)
                if not user:
                    raise UserNotFoundError(str(request.user_id))

                orders = await Order.filter(user=user).using_db(conn).all()
                return ListOrdersResponse(
                    root=[self.convert_database_model(order) for order in orders]
                )
            except UserNotFoundError as ve:
                self.logger.error(f"Validation error: {ve}")
                raise
            except Exception as e:
                self.logger.info(f"Unexpected error: {e}")
                raise CriticalError(f"Unexpected error: {e}")

    @service_method
    async def get_order(
        self: "Orders", redis: "ArqRedis", request: GetOrderRequest
    ) -> GetOrderResponse:
        async with in_transaction() as conn:
            try:
                order = await Order.get_or_none(id=request.order_id, using_db=conn)
                if not order or order.user.id != request.user_id:
                    raise OrderNotFoundError(str(request.order_id))
                return GetOrderResponse(root=self.convert_database_model(order))
            except OrderNotFoundError as ve:
                self.logger.error(f"Validation error: {ve}")
                raise
            except Exception as e:
                self.logger.info(f"Unexpected error: {e}")
                raise CriticalError(f"Unexpected error: {e}")

    @service_method
    async def cancel_order(
        self: "Orders", redis: "ArqRedis", request: CancelOrderRequest
    ) -> None:
        async with in_transaction() as conn:
            try:
                order = await Order.get_or_none(id=request.order_id, using_db=conn)
                if not order or order.user.id != request.user_id:
                    raise OrderNotFoundError(str(request.order_id))
                order.status = DatabaseOrderStatus.CANCELLED
                await order.save(using_db=conn)
            except OrderNotFoundError as ve:
                self.logger.error(f"Validation error: {ve}")
                raise
            except Exception as e:
                self.logger.info(f"Unexpected error: {e}")
                raise CriticalError(f"Unexpected error: {e}")
