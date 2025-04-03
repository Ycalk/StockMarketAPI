import logging
from tortoise import Tortoise
from .config import TORTOISE_ORM
from microkit.service import Service, service_method
from arq.connections import ArqRedis
from shared_models.users import User as UserSharedModel
from shared_models.users.create_user import CreateUserRequest
from .models import User


class Users(Service):
    async def init(self):
        self.logger = logging.getLogger("users")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas()
        self.logger.info("Database connection initialized.")

    # Methods
    @service_method
    async def create_user(self: "Users", redis: ArqRedis, request: CreateUserRequest) -> UserSharedModel:
        user = await User.create(**request.model_dump(exclude_unset=True))
        self.logger.info(f"User created with ID: {user.id}")
        return UserSharedModel.model_validate(user)
    