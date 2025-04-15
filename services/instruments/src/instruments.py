import logging
from tortoise import Tortoise
from database.config import TORTOISE_ORM
from microkit.service import Service, service_method
from arq.connections import ArqRedis


class Instruments(Service):
    async def init(self):
        self.logger = logging.getLogger("users")
        self.logger.info("Initializing database connection...")
        await Tortoise.init(config=TORTOISE_ORM)
        self.logger.info("Database connection initialized.")
    