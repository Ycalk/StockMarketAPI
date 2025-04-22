import logging
from arq import ArqRedis
import pytest
from tortoise import Tortoise
from ..src.users import Users
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
    users_service = Users()
    users_service.logger = logging.getLogger("users_test")
    return {
        "self": users_service,
        "redis": ArqRedis(),
    }
