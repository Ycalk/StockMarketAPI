from typing import Optional
from arq import ArqRedis
from microkit.service import Service, service_method
from database.config import TORTOISE_ORM
from tortoise.transactions import in_transaction
from tortoise.backends.base.client import TransactionContext
from database import Order, Balance, Instrument, User
from tortoise import Tortoise
import logging
from database.models.order import (
    OrderStatus as DatabaseOrderStatus,
    Direction as DatabaseOrderDirection,
    OrderType as DatabaseOrderType,
)
from shared_models.instruments.errors import InstrumentNotFoundError
from shared_models.users.errors import UserNotFoundError, InsufficientFundsError
from shared_models.orders.models.orders_bodies import LimitOrderBody
from shared_models.orders.errors import CriticalError
from shared_models.orders.requests.create_order import (
    CreateOrderRequest,
    CreateOrderResponse,
)
from shared_models.orders.models.orders_bodies.direction import Direction


class Orders(Service):
    async def init(self):
        self.logger = logging.getLogger("users")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        self.logger.info("Database connection initialized.")

    async def execute_orders(self, ticker: str) -> None:
        pass

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
                user = await User.get_or_none(
                    id=request.user_id, using_db=conn
                ).prefetch_related("balances")
                if not user:
                    raise UserNotFoundError(str(request.user_id))
                user_balance: Optional[Balance] = None
                for balance in user.balances:  # type: ignore
                    if balance.instrument.ticker == instrument.ticker:
                        user_balance = balance
                        break

                if request.body.direction == Direction.SELL:
                    maximum_to_sell = (
                        user_balance.amount
                        - await self.get_lock_balance(user, instrument, conn)
                        if user_balance
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
                await self.execute_orders(request.body.ticker)
