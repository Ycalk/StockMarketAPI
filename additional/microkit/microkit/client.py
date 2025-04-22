from typing import Optional
from arq.connections import RedisSettings
from arq import create_pool
from arq.connections import ArqRedis
from arq.jobs import Job


class MicroKitClient:
    """
    Client for interacting with a microkit services.
    Methods
    -------
        __call__(func_name: str, *args, **kwargs) -> Optional[Job]:
            Enqueues a job to the Redis queue.
    """

    def __init__(self, redis_settings: RedisSettings, service_name: str) -> None:
        """
        Initializes the MicroKitClient with Redis settings and service name.
        Parameters
        ----------
            redis_settings : RedisSettings
                settings for Redis connection
            service_name : str
                name of the service to interact with. Example: "Database"
        """
        self.redis_settings = redis_settings
        self.service_name = service_name
        self.redis: Optional[ArqRedis] = None

    async def __call__(self, func_name: str, *args, **kwargs) -> Optional[Job]:
        if not self.redis:
            self.redis = await create_pool(
                self.redis_settings, default_queue_name=self.service_name.lower()
            )
        return await self.redis.enqueue_job(
            f"{self.service_name}.{func_name}", *args, **kwargs
        )
