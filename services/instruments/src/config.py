import os
from dotenv import load_dotenv
load_dotenv()


class Config:
    VERBOSE = os.getenv("VERBOSE", "1") == "1"