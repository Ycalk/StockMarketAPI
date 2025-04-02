from concurrent.futures import ProcessPoolExecutor
import logging
import logging.config
from typing import Any, Optional
from arq import Worker
from arq.typing import SecondsTimedelta
from arq.connections import RedisSettings
from .service import Service
from .logs import default_log_config


class Runner:
    def __init__(self,
                 service_class: type[Service],
                 redis_settings: Optional[RedisSettings] = None, 
                 workers_count: int = 1,
                 max_jobs: int = 10,
                 job_timeout: SecondsTimedelta = 300,
                 keep_result: SecondsTimedelta = 3600,
                 keep_result_forever: bool = False,
                 max_tries: int = 5,
                 retry_jobs: bool = True,
                 logging_config: Optional[dict[str, Any]] = None) -> None:
        self._queue_name = service_class.__name__.lower()
        self._service = service_class()
        self._redis_settings = redis_settings or RedisSettings()
        self._workers_count = workers_count
        self._max_jobs = max_jobs
        self._job_timeout = job_timeout
        self._keep_result = keep_result
        self._keep_result_forever = keep_result_forever
        self._max_tries = max_tries
        self._retry_jobs = retry_jobs
        self.logging_config = logging_config or default_log_config(verbose=True)
        self.logger = logging.getLogger("microkit")
    
    @staticmethod
    async def _startup(ctx) -> None:
        await ctx['self'].init()
    
    @staticmethod
    async def _shutdown(ctx) -> None:
        await ctx['self'].shutdown()
    
    def _start_worker(self):
        logging.config.dictConfig(self.logging_config)
        worker = Worker(
            functions=self._service._functions,
            redis_settings=self._redis_settings,
            queue_name=self._queue_name,
            max_jobs=self._max_jobs,
            job_timeout=self._job_timeout,
            keep_result=self._keep_result,
            keep_result_forever=self._keep_result_forever,
            max_tries=self._max_tries,
            retry_jobs=self._retry_jobs,
            on_startup=Runner._startup,
            on_shutdown=Runner._shutdown,
            ctx={"self": self._service}
        )
        worker.run()
    
    def run(self):
        with ProcessPoolExecutor(max_workers=self._workers_count) as executor:
            executor.submit(self._start_worker)