from microkit.service import Runner
from src.orders import Orders  # type: ignore
from src.config import Config  # type: ignore
from microkit.service.logs import default_log_config
from arq.connections import RedisSettings


if __name__ == "__main__":
    logging_config = default_log_config(verbose=Config.VERBOSE)
    logging_level = "DEBUG" if Config.VERBOSE else "INFO"
    logging_config["loggers"]["orders"] = {
        "level": logging_level,
        "handlers": ["arq.standard"],
    }
    runner = Runner(
        Orders,
        logging_config=logging_config,
        redis_settings=RedisSettings(Config.REDIS_HOST, Config.REDIS_PORT),
        workers_count=Config.WORKERS_COUNT,
        poll_delay=0.0001,
    )
    runner.run()
