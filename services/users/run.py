from microkit.service import Runner
from src.users import Users # type: ignore
from src.config import Config # type: ignore
from microkit.service.logs import default_log_config


if __name__ == "__main__":
    logging_config = default_log_config(verbose=Config.VERBOSE)
    logging_level = "DEBUG" if Config.VERBOSE else "INFO"
    logging_config["loggers"]["users"] = {
        "level": logging_level,
        "handlers": ["arq.standard"],
    }
    runner = Runner(Users, logging_config=logging_config)
    runner.run()
