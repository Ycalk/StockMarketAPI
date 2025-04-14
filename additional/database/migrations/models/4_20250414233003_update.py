from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "orders" DROP CONSTRAINT IF EXISTS "fk_orders_instrume_85fec7b9";
        ALTER TABLE "orders" RENAME COLUMN "ticker_id" TO "instrument_id";
        CREATE TABLE IF NOT EXISTS "transactions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "quantity" INT NOT NULL,
    "price" INT NOT NULL,
    "executed_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "buyer_order_id" UUID REFERENCES "orders" ("id") ON DELETE CASCADE,
    "instrument_id" VARCHAR(10) NOT NULL REFERENCES "instruments" ("ticker") ON DELETE CASCADE,
    "seller_order_id" UUID REFERENCES "orders" ("id") ON DELETE CASCADE
);
        ALTER TABLE "orders" ADD CONSTRAINT "fk_orders_instrume_c9d283d3" FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("ticker") ON DELETE CASCADE;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "orders" DROP CONSTRAINT IF EXISTS "fk_orders_instrume_c9d283d3";
        ALTER TABLE "orders" RENAME COLUMN "instrument_id" TO "ticker_id";
        DROP TABLE IF EXISTS "transactions";
        ALTER TABLE "orders" ADD CONSTRAINT "fk_orders_instrume_85fec7b9" FOREIGN KEY ("ticker_id") REFERENCES "instruments" ("ticker") ON DELETE CASCADE;"""
