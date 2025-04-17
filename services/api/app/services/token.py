from typing import Optional
from uuid import UUID
from fastapi import HTTPException, Security
from starlette.requests import Request
from starlette.status import HTTP_403_FORBIDDEN
from pydantic import Field
from fastapi.security import APIKeyHeader
from fastapi.security.utils import get_authorization_scheme_param
import jwt
import os

SECRET_KEY = os.getenv('SECRET_KEY', '')
user_security = APIKeyHeader(name="Authorization", scheme_name="User authentication")

def generate_user_api_key(id: UUID) -> str:
    return jwt.encode({'id': str(id)}, SECRET_KEY, algorithm='HS256')

def verify_api_key(header_value: str = Security(user_security)) -> UUID:
    try:
        scheme, api_key = get_authorization_scheme_param(header_value)
        if not scheme or scheme.lower() != 'token':
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Invalid authentication scheme")
        if not api_key:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Missing API key")
        payload = jwt.decode(api_key, SECRET_KEY, algorithms=['HS256'])
        return UUID(payload['id'])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="API key expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid API key")