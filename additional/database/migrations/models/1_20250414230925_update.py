from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "instrument" (
    "ticker" VARCHAR(10) NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "instrument";"""
