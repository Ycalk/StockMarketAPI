import os
from dotenv import load_dotenv
from typing import Any, Dict, Union
from arq.connections import RedisSettings

load_dotenv()


class ApiServiceConfig:
    API_NAME = "Stock Market API"
    BASE_PREFIX = "/api/v1"
    DEFAULT_RESPONSE: Dict[Union[int, str], Dict[str, Any]] = {
        200: {"description": "Successful Response"}
    }
    LOGS_FOLDER = "logs"
    DEFAULT_POLL_DELAY = 0.0001


class RedisConfig:
    REDIS_SETTINGS = RedisSettings(
        os.getenv("REDIS_HOST", "localhost"), int(os.getenv("REDIS_PORT", "6379"))
    )
