from fastapi import APIRouter
from shared_models.users import User as UserSharedModel
from shared_models.users.create_user import CreateUserRequest
from ..models.public import RegisterUserRequest
from microkit.client import MicroKitClient
from ..config import RedisConfig


router = APIRouter(prefix="/public", tags=["public"])
users_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Users")


@router.post("/register", response_model=UserSharedModel)
async def register_user(request: RegisterUserRequest):
    job = await users_client("create_user", CreateUserRequest(**request.model_dump()))
    if job is None:
        raise ValueError("Job is None")
    return await job.result()