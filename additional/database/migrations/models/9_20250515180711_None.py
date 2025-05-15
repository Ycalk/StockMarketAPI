from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "instruments" (
    "ticker" VARCHAR(10) NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL
);
CREATE TABLE IF NOT EXISTS "users" (
    "id" UUID NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "role" VARCHAR(5) NOT NULL DEFAULT 'USER',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "users"."role" IS 'USER: USER\nADMIN: ADMIN';
CREATE TABLE IF NOT EXISTS "balances" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "amount" INT NOT NULL,
    "instrument_id" VARCHAR(10) NOT NULL REFERENCES "instruments" ("ticker") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_balances_user_id_624f8c" UNIQUE ("user_id", "instrument_id")
);
CREATE TABLE IF NOT EXISTS "balance_history" (
    "id" UUID NOT NULL PRIMARY KEY,
    "amount" INT NOT NULL,
    "operation_type" VARCHAR(8) NOT NULL,
    "executed_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "instrument_id" VARCHAR(10) NOT NULL REFERENCES "instruments" ("ticker") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "balance_history"."operation_type" IS 'DEPOSIT: DEPOSIT\nWITHDRAW: WITHDRAW';
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
    "instrument_id" VARCHAR(10) NOT NULL REFERENCES "instruments" ("ticker") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "orders"."type" IS 'LIMIT: LIMIT\nMARKET: MARKET';
COMMENT ON COLUMN "orders"."status" IS 'NEW: NEW\nEXECUTED: EXECUTED\nPARTIALLY_EXECUTED: PARTIALLY_EXECUTED\nCANCELLED: CANCELLED';
COMMENT ON COLUMN "orders"."direction" IS 'BUY: BUY\nSELL: SELL';
CREATE TABLE IF NOT EXISTS "transactions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "quantity" INT NOT NULL,
    "price" INT NOT NULL,
    "executed_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "buyer_order_id" UUID NOT NULL REFERENCES "orders" ("id") ON DELETE CASCADE,
    "instrument_id" VARCHAR(10) NOT NULL REFERENCES "instruments" ("ticker") ON DELETE CASCADE,
    "seller_order_id" UUID NOT NULL REFERENCES "orders" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
