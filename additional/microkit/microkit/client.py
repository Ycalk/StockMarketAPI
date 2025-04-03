from typing import Optional
from arq.connections import RedisSettings
from arq import create_pool
from arq.connections import ArqRedis


class MicroKitClient:
    def __init__(self, redis_settings: RedisSettings, service_name: str) -> None:
        self.redis_settings = redis_settings
        self.service_name = service_name
        self.queue_name = service_name.lower()
        self.redis: Optional[ArqRedis] = None
    
    async def __call__(self, func_name: str, *args, **kwargs) -> None:
        if not self.redis:
            self.redis = await create_pool(self.redis_settings, default_queue_name=self.queue_name)
        await self.redis.enqueue_job(func_name, *args, **kwargs)