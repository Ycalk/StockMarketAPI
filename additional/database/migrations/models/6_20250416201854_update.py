from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "balance_history" DROP CONSTRAINT IF EXISTS "fk_balance__users_9147fb6d";
        ALTER TABLE "balance_history" DROP COLUMN "executed_by_id";"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "balance_history" ADD "executed_by_id" UUID;
        ALTER TABLE "balance_history" ADD CONSTRAINT "fk_balance__users_9147fb6d" FOREIGN KEY ("executed_by_id") REFERENCES "users" ("id") ON DELETE CASCADE;"""
