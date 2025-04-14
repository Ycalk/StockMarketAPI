from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
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
    "executed_by_id" UUID REFERENCES "users" ("id") ON DELETE CASCADE,
    "instrument_id" VARCHAR(10) NOT NULL REFERENCES "instruments" ("ticker") ON DELETE CASCADE,
    "user_id" UUID NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "balance_history"."operation_type" IS 'DEPOSIT: DEPOSIT\nWITHDRAW: WITHDRAW';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "balances";
        DROP TABLE IF EXISTS "balance_history";"""
