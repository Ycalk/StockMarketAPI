import logging
from logging.handlers import RotatingFileHandler
from logging import Logger
import os
from .config import ApiServiceConfig


def get_logger(name: str) -> Logger:
    filename = f"{ApiServiceConfig.LOGS_FOLDER}/{name}.log"
    common_logger_file_path = f"{ApiServiceConfig.LOGS_FOLDER}/common.log"
    
    os.makedirs(ApiServiceConfig.LOGS_FOLDER, exist_ok=True)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    os.makedirs(os.path.dirname(common_logger_file_path), exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.hasHandlers():
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler = RotatingFileHandler(filename, maxBytes=5_000_000, backupCount=3)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        common_handler = RotatingFileHandler(common_logger_file_path, maxBytes=5_000_000, backupCount=3)
        common_handler.setFormatter(formatter)
        logger.addHandler(common_handler)
    return logger

def log_action(action: str, identifier: str, result: str, duration: float, logger: Logger | str):
    if isinstance(logger, str):
        logger = logging.getLogger(logger)
    message = f"{action} {identifier} -> {result} in {duration:.2f}s"
    if result.startswith("200"):
        logger.info(message)
    elif result.startswith("500"):
        logger.critical(message)
    else:
        logger.error(message)