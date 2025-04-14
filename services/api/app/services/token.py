from uuid import UUID
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
import jwt
from shared_models.users.user import UserRole, User
import os


SECRET_KEY = os.getenv('SECRET_KEY', '')
api_key_header = APIKeyHeader(name="Authorization", auto_error=True)

def generate_api_key(id: UUID) -> str:
    return jwt.encode({'id': str(id)}, SECRET_KEY, algorithm='HS256')

def verify_api_key(api_key: str = Security(api_key_header)) -> UUID:
    try:
        payload = jwt.decode(api_key, SECRET_KEY, algorithms=['HS256'])
        return UUID(payload['id'])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="API key expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid API key")