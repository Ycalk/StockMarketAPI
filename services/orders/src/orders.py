from microkit.service import Service
from database.config import TORTOISE_ORM
from tortoise import Tortoise
import logging


class Orders(Service):
    async def init(self):
        self.logger = logging.getLogger("users")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        self.logger.info("Database connection initialized.")