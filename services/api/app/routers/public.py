from fastapi import APIRouter
from ..models.public import RegisterUserRequest
from ..models.user import User as UserAPIModel
from microkit.client import MicroKitClient
from ..config import RedisConfig
from shared_models.users.create_user import CreateUserRequest, CreateUserResponse
from shared_models.instruments.get_instruments import GetInstrumentsResponse


router = APIRouter(prefix="/public", tags=["public"])
users_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Users")
instruments_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Instruments")


@router.post("/register", response_model=UserAPIModel)
async def register_user(request: RegisterUserRequest):
    job = await users_client("create_user", CreateUserRequest(**request.model_dump()))
    if job is None:
        raise ValueError("Job is None")
    model: CreateUserResponse = await job.result()
    return UserAPIModel(**model.user.model_dump())


@router.get("/instrument", response_model=GetInstrumentsResponse)
async def get_instruments():
    job = await instruments_client("get_instruments")
    if job is None:
        raise ValueError("Job is None")
    return await job.result()