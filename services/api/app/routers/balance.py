import time
from fastapi import APIRouter, Depends, HTTPException
from microkit import MicroKitClient
from uuid import UUID
from shared_models.users.get_balance import GetBalanceRequest, GetBalanceResponse
from shared_models.users.errors import CriticalError, UserNotFoundError
from ..config import RedisConfig
from ..services.token import verify_user_api_key
from ..models.error import ErrorResponse
from ..logging import log_action
import asyncio


router = APIRouter(prefix="/balance", tags=["balance"])
users_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Users")


@router.get(
    "",
    response_model=GetBalanceResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_balance(user_id: UUID = Depends(verify_user_api_key)):
    start = time.time()
    job = await users_client("get_balance", GetBalanceRequest(user_id=user_id))
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        result = "200 (OK)"
        return await job.result(timeout=10, poll_delay=0.1)
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except UserNotFoundError as e:
        result = "404 (User Not Found)"
        raise HTTPException(status_code=404, detail=e.message)
    except CriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        log_action("GET BALANCE", str(user_id), result, duration, "balance")
