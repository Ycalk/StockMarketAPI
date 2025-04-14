from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "instrument" RENAME TO "instruments";
        ALTER TABLE "instruments" ALTER COLUMN "name" TYPE VARCHAR(255) USING "name"::VARCHAR(255);
        ALTER TABLE "user" RENAME TO "users";
        ALTER TABLE "users" ALTER COLUMN "role" SET DEFAULT 'USER';
        COMMENT ON COLUMN "users"."role" IS 'USER: USER
ADMIN: ADMIN';
        ALTER TABLE "users" ALTER COLUMN "name" TYPE VARCHAR(255) USING "name"::VARCHAR(255);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "users" RENAME TO "user";
        ALTER TABLE "users" ALTER COLUMN "role" SET DEFAULT 'user';
        COMMENT ON COLUMN "users"."role" IS 'USER: user
ADMIN: admin';
        ALTER TABLE "users" ALTER COLUMN "name" TYPE VARCHAR(100) USING "name"::VARCHAR(100);
        ALTER TABLE "instruments" RENAME TO "instrument";
        ALTER TABLE "instruments" ALTER COLUMN "name" TYPE VARCHAR(100) USING "name"::VARCHAR(100);"""
