import logging
from tortoise import Tortoise
from tortoise.transactions import in_transaction
from database.config import TORTOISE_ORM
from microkit.service import Service, service_method
from arq.connections import ArqRedis
from shared_models.users import User as UserSharedModel
from shared_models.users.create_user import CreateUserRequest, CreateUserResponse
from shared_models.users.delete_user import DeleteUserRequest, DeleteUserResponse
from shared_models.users.get_user import GetUserRequest, GetUserResponse
from shared_models.users.deposit import DepositRequest
from shared_models.users.withdraw import WithdrawRequest
from shared_models.users.get_balance import GetBalanceRequest, GetBalanceResponse
from shared_models.users.errors import (
    CriticalError,
    UserNotFoundError,
    InsufficientFundsError,
)
from shared_models.instruments.errors import InstrumentNotFoundError
from database import User, BalanceHistory, Balance, Instrument
from database.models.balance_history import OperationType


class Users(Service):
    async def init(self):
        self.logger = logging.getLogger("users")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        self.logger.info("Database connection initialized.")

    # Methods
    @service_method
    async def create_user(
        self: "Users", redis: ArqRedis, request: CreateUserRequest
    ) -> CreateUserResponse:
        try:
            user = await User.create(**request.model_dump(exclude_unset=True))
            rub_instrument, _ = await Instrument.get_or_create(
                ticker="RUB", defaults={"name": "Russian Ruble"}
            )
            await Balance.create(user=user, instrument=rub_instrument, amount=0)
            self.logger.info(f"User created with ID: {user.id}")
            return CreateUserResponse(user=UserSharedModel.model_validate(user))
        except Exception as e:
            self.logger.critical(f"Error creating user: {e}")
            raise CriticalError(f"Error creating user: {e}")

    @service_method
    async def delete_user(
        self: "Users", redis: ArqRedis, request: DeleteUserRequest
    ) -> DeleteUserResponse:
        async with in_transaction() as conn:
            try:
                user = (
                    await User.filter(id=request.id)
                    .select_for_update()
                    .using_db(conn)
                    .first()
                )
                if not user:
                    self.logger.warning(f"User with ID {request.id} not found.")
                    raise UserNotFoundError(str(request.id))

                await user.delete()
                self.logger.info(f"User with ID {request.id} deleted.")
                return DeleteUserResponse(user=UserSharedModel.model_validate(user))
            except UserNotFoundError as nf:
                self.logger.error(f"Validation error in delete_user: {nf}")
                raise
            except Exception as e:
                msg = f"Delete operation failed: {e}"
                self.logger.critical(msg)
                raise CriticalError(msg)

    @service_method
    async def get_user(
        self: "Users", redis: ArqRedis, request: GetUserRequest
    ) -> GetUserResponse:
        try:
            user = await User.get_or_none(id=request.id)
            if not user:
                self.logger.warning(f"User with ID {request.id} not found.")
                raise UserNotFoundError(str(request.id))
            return GetUserResponse(user=UserSharedModel.model_validate(user))
        except UserNotFoundError as ve:
            self.logger.error(f"Validation error in get_user: {ve}")
            raise
        except Exception as e:
            msg = f"Get operation failed: {e}"
            self.logger.critical(msg)
            raise CriticalError(msg)

    @service_method
    async def deposit(self: "Users", redis: ArqRedis, request: DepositRequest):
        async with in_transaction() as conn:
            try:
                user = (
                    await User.filter(id=request.user_id)
                    .select_for_update()
                    .using_db(conn)
                    .first()
                )
                if not user:
                    self.logger.warning(f"User {request.user_id} not found")
                    raise UserNotFoundError(str(request.user_id))

                instrument = await Instrument.get_or_none(
                    ticker=request.ticker, using_db=conn
                )
                if not instrument:
                    self.logger.warning(f"Instrument {request.ticker} not found")
                    raise InstrumentNotFoundError(request.ticker)

                balance, created = await Balance.get_or_create(
                    user=user,
                    instrument=instrument,
                    defaults={"amount": request.amount},
                    using_db=conn,
                )

                if not created:
                    balance.amount += request.amount
                    await balance.save(using_db=conn)

                await BalanceHistory.create(
                    user=user,
                    instrument=instrument,
                    amount=request.amount,
                    operation_type=OperationType.DEPOSIT,
                    using_db=conn,
                )
            except (UserNotFoundError, InstrumentNotFoundError) as ve:
                self.logger.error(f"Validation error in deposit: {ve}")
                raise
            except Exception as e:
                msg = f"Deposit operation failed: {e}"
                self.logger.critical(msg)
                raise CriticalError(msg)

        self.logger.info(
            f"Successfully deposited {request.amount} {request.ticker} "
            f"to user {request.user_id}. New balance: {balance.amount}"
        )

    @service_method
    async def withdraw(self: "Users", redis: ArqRedis, request: WithdrawRequest):
        async with in_transaction() as conn:
            try:
                user = (
                    await User.filter(id=request.user_id)
                    .select_for_update()
                    .using_db(conn)
                    .first()
                )
                if not user:
                    self.logger.warning(f"User {request.user_id} not found")
                    raise UserNotFoundError(str(request.user_id))

                instrument = await Instrument.get_or_none(
                    ticker=request.ticker, using_db=conn
                )
                if not instrument:
                    self.logger.warning(f"Instrument {request.ticker} not found")
                    raise InstrumentNotFoundError(request.ticker)

                balance = await Balance.get_or_none(
                    user=user, instrument=instrument, using_db=conn
                )

                if not balance:
                    self.logger.warning(
                        f"Balance for user {request.user_id} and instrument {request.ticker} not found"
                    )
                    raise InsufficientFundsError(
                        str(request.user_id), request.amount, 0
                    )

                if balance.amount < request.amount:
                    self.logger.warning(
                        f"Insufficient funds for user {request.user_id} in {request.ticker}"
                    )
                    raise InsufficientFundsError(
                        str(request.user_id), request.amount, balance.amount
                    )

                balance.amount -= request.amount
                await balance.save(using_db=conn)

                await BalanceHistory.create(
                    user=user,
                    instrument=instrument,
                    amount=request.amount,
                    operation_type=OperationType.WITHDRAW,
                    using_db=conn,
                )

            except (
                UserNotFoundError,
                InstrumentNotFoundError,
                InsufficientFundsError,
            ) as ve:
                self.logger.error(f"Validation error in withdraw: {ve}")
                raise
            except Exception as e:
                msg = f"Withdraw operation failed: {e}"
                self.logger.critical(msg)
                raise CriticalError(msg)

        self.logger.info(
            f"Successfully withdrawn {request.amount} {request.ticker} "
            f"from user {request.user_id}. New balance: {balance.amount}"
        )

    @service_method
    async def get_balance(
        self: "Users", redis: ArqRedis, request: GetBalanceRequest
    ) -> GetBalanceResponse:
        async with in_transaction() as conn:
            try:
                user = await User.get_or_none(id=request.user_id, using_db=conn)
                if not user:
                    self.logger.warning(f"User {request.user_id} not found")
                    raise UserNotFoundError(str(request.user_id))

                balances = await Balance.filter(user=user).using_db(conn).all()

                return GetBalanceResponse(
                    root={
                        (await balance.instrument).ticker: balance.amount
                        for balance in balances
                    }
                )
            except UserNotFoundError as ve:
                self.logger.error(f"Validation error in get_balance: {ve}")
                raise
            except Exception as e:
                msg = f"Get balance operation failed: {e}"
                self.logger.critical(msg)
                raise CriticalError(msg)
