import logging
from arq import ArqRedis
import pytest
from tortoise import Tortoise
from ..src.instruments import Instruments
import pytest_asyncio


@pytest_asyncio.fixture(scope="function", autouse=True, loop_scope="session")
async def setup_database():
    config = {
        "connections": {"default": "sqlite://:memory:"},
        "apps": {
            "models": {
                "models": ["database.models"],
                "default_connection": "default",
            }
        },
    }
    await Tortoise.init(config)
    await Tortoise.generate_schemas()
    yield
    await Tortoise._drop_databases()
    await Tortoise.close_connections()


@pytest.fixture(scope="session")
def ctx() -> dict:
    instruments_service = Instruments()
    instruments_service.logger = logging.getLogger("instruments_test")
    return {
        "self": instruments_service,
        "redis": ArqRedis(),
    }
