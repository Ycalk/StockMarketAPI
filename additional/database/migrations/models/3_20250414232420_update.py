from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "orders" (
    "id" UUID NOT NULL PRIMARY KEY,
    "type" VARCHAR(6) NOT NULL,
    "status" VARCHAR(18) NOT NULL DEFAULT 'NEW',
    "direction" VARCHAR(4) NOT NULL,
    "quantity" INT NOT NULL,
    "price" INT,
    "filled" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ticker_id" VARCHAR(10) NOT NULL REFERENCES "instruments" ("ticker") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "orders"."type" IS 'LIMIT: LIMIT\nMARKET: MARKET';
COMMENT ON COLUMN "orders"."status" IS 'NEW: NEW\nEXECUTED: EXECUTED\nPARTIALLY_EXECUTED: PARTIALLY_EXECUTED\nCANCELLED: CANCELLED';
COMMENT ON COLUMN "orders"."direction" IS 'BUY: BUY\nSELL: SELL';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "orders";"""
