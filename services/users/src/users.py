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
        user = await User.create(**request.model_dump(exclude_unset=True))
        self.logger.info(f"User created with ID: {user.id}")
        return UserSharedModel.model_validate(user)
    
    @service_method
    async def delete_user(self: "Users", redis: ArqRedis, request: DeleteUserRequest) -> UserSharedModel:
        user = await User.get_or_none(id=request.id)
        if not user:
            self.logger.warning(f"User with ID {request.id} not found.")
            raise ValueError(f"User with ID {request.id} not found.")
        await user.delete()
        self.logger.info(f"User with ID {request.id} deleted.")
        return UserSharedModel.model_validate(user)
    
    @service_method
    async def get_user(self: "Users", redis: ArqRedis, request: GetUserRequest) -> UserSharedModel:
        user = await User.get_or_none(id=request.id)
        if not user:
            self.logger.warning(f"User with ID {request.id} not found.")
            raise ValueError(f"User with ID {request.id} not found.")
        return UserSharedModel.model_validate(user)
    
    @service_method
    async def deposit(self: "Users", redis: ArqRedis, request: DepositRequest):
        try:
            async with in_transaction() as conn:
                user = await User.get_or_none(id=request.user_id, using_db=conn)
                if not user:
                    self.logger.warning(f"User with ID {request.user_id} not found.")
                    raise ValueError(f"User with ID {request.user_id} not found.")
                
                instrument = await Instrument.get_or_none(ticker=request.ticker, using_db=conn)
                if not instrument:
                    self.logger.warning(f"Instrument with ticker {request.ticker} not found.")
                    raise ValueError(f"Instrument with ticker {request.ticker} not found.")
                
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
            self.logger.info(f"Deposit of {request.amount} for user {request.user_id} in instrument {request.ticker} completed.")
        except Exception as e:
            self.logger.error(f"Error during deposit: {e}")
            raise ValueError(f"Error during deposit: {e}")
        
    