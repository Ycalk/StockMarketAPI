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
from shared_models.orders.errors import CriticalError, OrderNotFoundError, CannotCancelOrderError
from shared_models.orders.requests.create_order import (
    CreateOrderRequest,
    CreateOrderResponse,
)
from shared_models.orders.models.orders_bodies.direction import Direction
from shared_models.orders.requests.list_orders import (
    ListOrdersRequest,
    ListOrdersResponse,
)
from shared_models.orders.requests.get_orderbook import (
    GetOrderbookRequest,
    GetOrderbookResponse,
    OrderbookItem,
)
from shared_models.orders.requests.get_transactions import (
    GetTransactionsRequest,
    GetTransactionsResponse,
    Transaction as TransactionSharedModel,
)
from shared_models.orders.requests.get_order import (
    GetOrderRequest,
    GetOrderResponse,
)
from shared_models.orders.requests.cancel_order import CancelOrderRequest


class Orders(Service):
    async def init(self) -> None:
        self.logger = logging.getLogger("orders")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas(safe=True)
        self.logger.info("Database connection initialized.")

    async def shutdown(self) -> None:
        self.logger.info("Closing connections...")
        await Tortoise.close_connections()
        self.logger.info("Connections closed.")

    async def execute_transaction(
        self, transaction: Transaction, context: TransactionContext
    ) -> None:
        buyer = transaction.buyer_order.user
        seller = transaction.seller_order.user
        instrument_id = transaction.instrument.ticker
        quantity = transaction.quantity
        total_price = quantity * transaction.price

        for order in (transaction.buyer_order, transaction.seller_order):
            order.filled += quantity
            if order.filled == order.quantity:
                order.status = DatabaseOrderStatus.EXECUTED

        buyer_balance, _ = await Balance.get_or_create(
            user=buyer,
            instrument_id=instrument_id,
            using_db=context,  # type: ignore
            defaults={"amount": 0},
        )

        if buyer == seller:
            # self trade
            if buyer_balance.amount < quantity:
                raise CriticalError(
                    f"User does not have enough {instrument_id} to self-trade"
                )
            buyer_rub_balance, _ = await Balance.get_or_create(
                user=buyer,
                instrument_id="RUB",
                using_db=context,  # type: ignore
                defaults={"amount": 0},
            )
            if buyer_rub_balance.amount < total_price:
                raise CriticalError("User does not have enough RUB to self-trade")
        else:
            seller_balance = await Balance.get_or_none(
                user=seller,
                instrument_id=instrument_id,
                using_db=context,  # type: ignore
            )
            if seller_balance is None or seller_balance.amount < quantity:
                raise CriticalError(
                    f"Seller does not have enough {instrument_id} to sell"
                )

            seller_balance.amount -= quantity
            buyer_balance.amount += quantity

            buyer_rub_balance = await Balance.get_or_none(
                user=buyer,
                instrument_id="RUB",
                using_db=context,  # type: ignore
            )
            seller_rub_balance, _ = await Balance.get_or_create(
                user=seller,
                instrument_id="RUB",
                using_db=context,  # type: ignore
                defaults={"amount": 0},
            )
            if buyer_rub_balance is None or buyer_rub_balance.amount < total_price:
                raise CriticalError("Buyer does not have enough RUB to buy")

            buyer_rub_balance.amount -= total_price
            seller_rub_balance.amount += total_price

            for balance in (
                buyer_balance,
                seller_balance,
                buyer_rub_balance,
                seller_rub_balance,
            ):
                await balance.save(using_db=context)  # type: ignore
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
            instrument_id="RUB",
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
                .prefetch_related("instrument", "user")
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
                .prefetch_related("instrument", "user")
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
                .prefetch_related("instrument", "user")
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

    async def get_lock_rubs(self, user: User, context: TransactionContext) -> int:
        user_orders = await (
            Order.filter(
                user=user,
                status=DatabaseOrderStatus.NEW,
                direction=DatabaseOrderDirection.BUY,
            )
            .using_db(context)  # type: ignore
            .all()
        )
        return sum(
            (order.quantity - order.filled) * order.price for order in user_orders
        )

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
                    qty=database_model.quantity,
                ),
            )
        else:
            order_status = SharedModelOrderStatus(database_model.status)
            if (
                order_status == SharedModelOrderStatus.NEW
                and database_model.filled != 0
            ):
                order_status = SharedModelOrderStatus.PARTIALLY_EXECUTED
            return LimitOrder(
                id=database_model.id,
                status=order_status,
                user_id=database_model.user.id,
                timestamp=database_model.created_at,
                body=LimitOrderBody(
                    direction=SharedModelOrderDirection(database_model.direction.value),
                    ticker=database_model.instrument.ticker,
                    qty=database_model.quantity,
                    price=database_model.price,
                ),
                filled=database_model.filled,
            )

    @service_method
    async def create_order(
        self: "Orders", redis: "ArqRedis", request: CreateOrderRequest
    ) -> CreateOrderResponse:
        try:
            async with in_transaction() as conn:
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
                        raise InsufficientFundsError(str(user.id), request.body.qty, 0)
                    maximum_to_sell = (
                        balance.amount
                        - await self.get_lock_balance(user, instrument, conn)
                        if balance
                        else 0
                    )
                    if maximum_to_sell < request.body.qty:
                        raise InsufficientFundsError(
                            str(user.id), request.body.qty, maximum_to_sell
                        )
                elif request.body.direction == Direction.BUY and isinstance(
                    request.body, LimitOrderBody
                ):
                    rub_balance = await Balance.get_or_none(
                        user=user, instrument_id="RUB", using_db=conn
                    )
                    if rub_balance is None:
                        raise InsufficientFundsError(
                            str(user.id), request.body.qty * request.body.price, 0
                        )
                    maximum_to_buy = rub_balance.amount - await self.get_lock_rubs(
                        user, conn
                    )
                    if maximum_to_buy < request.body.qty * request.body.price:
                        raise InsufficientFundsError(
                            str(user.id),
                            request.body.qty * request.body.price,
                            maximum_to_buy,
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
                    "quantity": request.body.qty,
                }

                if isinstance(request.body, LimitOrderBody):
                    order_data["price"] = request.body.price
                order = await Order.create(using_db=conn, **order_data)
            lock = redis.lock(f"lock:orders:{request.body.ticker}", timeout=5)
            async with lock:
                await self.execute_orders(request.body.ticker)
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

    @service_method
    async def list_orders(
        self: "Orders", redis: "ArqRedis", request: ListOrdersRequest
    ) -> ListOrdersResponse:
        async with in_transaction() as conn:
            try:
                user = await User.get_or_none(id=request.user_id, using_db=conn)
                if not user:
                    raise UserNotFoundError(str(request.user_id))

                orders = (
                    await Order.filter(user=user)
                    .using_db(conn)
                    .prefetch_related("user", "instrument")
                    .all()
                )
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
                order = await Order.get_or_none(
                    id=request.order_id, using_db=conn
                ).prefetch_related("user", "instrument")
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
                order = await Order.get_or_none(
                    id=request.order_id, using_db=conn
                ).prefetch_related("user")
                if not order or order.user.id != request.user_id:
                    raise OrderNotFoundError(str(request.order_id))
                if order.type == DatabaseOrderType.MARKET:
                    raise CannotCancelOrderError("Market orders cannot be cancelled")
                if order.status in (DatabaseOrderStatus.EXECUTED, DatabaseOrderStatus.PARTIALLY_EXECUTED):
                    raise CannotCancelOrderError("Orders with status EXECUTED or PARTIALLY_EXECUTED cannot be cancelled")
                if order.status == DatabaseOrderStatus.CANCELLED:
                    raise CannotCancelOrderError("Order is already cancelled")
                order.status = DatabaseOrderStatus.CANCELLED
                await order.save(using_db=conn)
            except (OrderNotFoundError, CannotCancelOrderError) as ve:
                self.logger.error(f"Validation error: {ve}")
                raise
            except Exception as e:
                self.logger.info(f"Unexpected error: {e}")
                raise CriticalError(f"Unexpected error: {e}")

    @service_method
    async def get_orderbook(
        self: "Orders", redis: "ArqRedis", request: GetOrderbookRequest
    ) -> GetOrderbookResponse:
        async with in_transaction() as conn:
            try:
                instrument = await Instrument.get_or_none(ticker=request.ticker)
                if not instrument:
                    raise InstrumentNotFoundError(str(request.ticker))
                orders = (
                    await Order.filter(
                        instrument=instrument,
                        status=DatabaseOrderStatus.NEW,
                        type=DatabaseOrderType.LIMIT,
                    )
                    .using_db(conn)
                    .all()
                )
                buy: dict[int, int] = {}
                sell: dict[int, int] = {}
                for order in orders:
                    if order.direction == DatabaseOrderDirection.BUY:
                        buy[order.price] = (
                            buy.get(order.price, 0) + order.quantity - order.filled
                        )
                    else:
                        sell[order.price] = (
                            sell.get(order.price, 0) + order.quantity - order.filled
                        )
                return GetOrderbookResponse(
                    bid_levels=[
                        OrderbookItem(price=price, qty=qty)
                        for price, qty in sorted(buy.items(), key=lambda x: -x[0])[
                            : request.limit
                        ]
                    ],
                    ask_levels=[
                        OrderbookItem(price=price, qty=qty)
                        for price, qty in sorted(sell.items(), key=lambda x: x[0])[
                            : request.limit
                        ]
                    ],
                )
            except InstrumentNotFoundError as ve:
                self.logger.error(f"Validation error: {ve}")
                raise
            except Exception as e:
                self.logger.info(f"Unexpected error: {e}")
                raise CriticalError(f"Unexpected error: {e}")

    @service_method
    async def get_transactions(
        self: "Orders", redis: "ArqRedis", request: GetTransactionsRequest
    ) -> GetTransactionsResponse:
        async with in_transaction() as conn:
            try:
                instrument = await Instrument.get_or_none(ticker=request.ticker)
                if not instrument:
                    raise InstrumentNotFoundError(str(request.ticker))
                transactions = (
                    await Transaction.filter(instrument=instrument)
                    .using_db(conn)
                    .order_by("-executed_at")
                    .all()
                )

                return GetTransactionsResponse(
                    root=[
                        TransactionSharedModel(
                            ticker=instrument.ticker,
                            amount=tx.quantity,
                            price=tx.price,
                            timestamp=tx.executed_at,
                        )
                        for tx in transactions[:request.limit]
                    ]
                )
            except InstrumentNotFoundError as ve:
                self.logger.error(f"Validation error: {ve}")
                raise
            except Exception as e:
                self.logger.info(f"Unexpected error: {e}")
                raise CriticalError(f"Unexpected error: {e}")
