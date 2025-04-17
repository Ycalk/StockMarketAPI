from fastapi import APIRouter, Depends
from microkit import MicroKitClient
from uuid import UUID
from shared_models.users.get_balance import GetBalanceRequest, GetBalanceResponse
from ..config import RedisConfig
from ..services.token import verify_api_key


router = APIRouter(prefix="/balance", tags=["balance"])
users_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Users")


@router.get("", response_model=GetBalanceResponse)
async def get_balance(user_id: UUID = Depends(verify_api_key)):
    job = await users_client("get_balance", GetBalanceRequest(user_id=user_id))
    if job is None:
        raise ValueError("Job is None")
    return await job.result()