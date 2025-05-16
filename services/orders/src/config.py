import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    VERBOSE = os.getenv("VERBOSE", "1") == "1"
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    WORKERS_COUNT = int(os.getenv("WORKERS_COUNT", "1"))
