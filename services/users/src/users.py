import logging
from tortoise import Tortoise
from tortoise.transactions import in_transaction
from database.config import TORTOISE_ORM
from microkit.service import Service, service_method
from arq.connections import ArqRedis
from shared_models.users import User as UserSharedModel
from shared_models.users.create_user import CreateUserRequest
from shared_models.users.delete_user import DeleteUserRequest
from shared_models.users.get_user import GetUserRequest
from shared_models.users.deposit import DepositRequest
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
    async def create_user(self: "Users", redis: ArqRedis, request: CreateUserRequest) -> UserSharedModel:
        try:
            user = await User.create(**request.model_dump(exclude_unset=True))
            self.logger.info(f"User created with ID: {user.id}")
            return UserSharedModel.model_validate(user)
        except Exception as e:
            self.logger.critical(f"Error creating user: {e}")
            raise ValueError(f"Error creating user: {e}")
    
    @service_method
    async def delete_user(self: "Users", redis: ArqRedis, request: DeleteUserRequest) -> UserSharedModel:
        async with in_transaction() as conn:
            try:
                user = await User.get_or_none(id=request.id)
                if not user:
                    self.logger.warning(f"User with ID {request.id} not found.")
                    raise ValueError(f"User with ID {request.id} not found.")

                await user.delete()
                self.logger.info(f"User with ID {request.id} deleted.")
                return UserSharedModel.model_validate(user)
            except ValueError as ve:
                self.logger.error(f"Validation error in delete_user: {ve}")
                raise
            except Exception as e:
                self.logger.critical(f"Unexpected error in delete_user: {e}")
                raise ValueError(f"Delete operation failed: {str(e)}")
    
    @service_method
    async def get_user(self: "Users", redis: ArqRedis, request: GetUserRequest) -> UserSharedModel:
        try:
            user = await User.get_or_none(id=request.id)
            if not user:
                self.logger.warning(f"User with ID {request.id} not found.")
                raise ValueError(f"User with ID {request.id} not found.")
            return UserSharedModel.model_validate(user)
        except ValueError as ve:
            self.logger.error(f"Validation error in get_user: {ve}")
            raise
        except Exception as e:
            self.logger.critical(f"Unexpected error in get_user: {e}")
            raise ValueError(f"Get operation failed: {str(e)}")
    
    @service_method
    async def deposit(self: "Users", redis: ArqRedis, request: DepositRequest):
        async with in_transaction() as conn:
            try:
                user = await User.filter(id=request.user_id).select_for_update().using_db(conn).first()
                if not user:
                    error_msg = f"User {request.user_id} not found"
                    self.logger.warning(error_msg)
                    raise ValueError(error_msg)
                
                instrument = await Instrument.get_or_none(ticker=request.ticker, using_db=conn)
                if not instrument:
                    error_msg = f"Instrument {request.ticker} not found"
                    self.logger.warning(error_msg)
                    raise ValueError(error_msg)
                
                balance, created = await Balance.get_or_create(
                    user=user,
                    instrument=instrument,
                    defaults={"amount": request.amount},
                    using_db=conn
                )
                
                if not created:
                    balance.amount += request.amount
                    await balance.save(using_db=conn)

                await BalanceHistory.create(
                    user=user,
                    instrument=instrument,
                    amount=request.amount,
                    operation_type=OperationType.DEPOSIT,
                    using_db=conn
                )
                
            except ValueError as ve:
                self.logger.error(f"Validation error in deposit: {ve}")
                raise
            except Exception as e:
                self.logger.critical(f"Unexpected error in deposit: {e}")
                raise ValueError(f"Deposit operation failed: {str(e)}")

        self.logger.info(
            f"Successfully deposited {request.amount} {request.ticker} "
            f"to user {request.user_id}. New balance: {balance.amount}"
        )
        
    