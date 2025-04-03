import os
from dotenv import load_dotenv
load_dotenv()


TORTOISE_ORM = {
    'connections': {
        'default': {
            'engine': 'tortoise.backends.asyncpg',
            'credentials': {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5432'),
                'user': os.getenv('DB_USER', 'users'),
                'password': os.getenv('DB_PASSWORD', 'users'),
                'database': os.getenv('DB_NAME', 'users'),
            }
        },
    },
    'apps': {
        'models': {
            'models': ['src.models'],
            'default_connection': 'default',
        }
    }
}

class Config:
    VERBOSE = os.getenv("VERBOSE", "1") == "1"