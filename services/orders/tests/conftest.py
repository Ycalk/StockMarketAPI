import logging
from arq import ArqRedis
from database import Instrument, User
import pytest
from tortoise import Tortoise
from ..src.orders import Orders
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


@pytest.fixture(scope="function")
def ctx() -> dict:
    order_service = Orders()
    order_service.logger = logging.getLogger("orders_test")
    return {
        "self": order_service,
        "redis": ArqRedis(),
    }


@pytest_asyncio.fixture(scope="function")
async def instrument() -> Instrument:
    return await Instrument.create(ticker="AAPL", name="Apple Inc.")


@pytest_asyncio.fixture(scope="function")
async def user() -> User:
    return await User.create(name="Test user")


@pytest_asyncio.fixture(scope="function")
async def rub() -> Instrument:
    return await Instrument.create(name="Russian Ruble", ticker="RUB")
