from fastapi import APIRouter
from microkit import MicroKitClient
from ..config import RedisConfig
from shared_models.instruments.add_instrument import AddInstrumentRequest
from shared_models.instruments import Instrument as InstrumentSharedModel
from shared_models.instruments.delete_instrument import DeleteInstrumentRequest
from shared_models.users.delete_user import DeleteUserRequest, DeleteUserResponse
from shared_models.users.deposit import DepositRequest
from shared_models.users.withdraw import WithdrawRequest
from ..models.user import User as UserAPIModel
from ..models.response_status import ResponseStatus
from ..services.token import verify_admin_api_key
from fastapi import Depends
from uuid import UUID


router = APIRouter(prefix="/admin", tags=["admin"])
instruments_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Instruments")
users_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Users")


@router.delete("/user/{user_id}", response_model=UserAPIModel)
async def delete_user(user_id: UUID, _:None = Depends(verify_admin_api_key)):
    job = await users_client("delete_user", DeleteUserRequest(id=user_id))
    if job is None:
        raise ValueError("Job is None")
    model: DeleteUserResponse = await job.result()
    return UserAPIModel(**model.user.model_dump())


@router.post("/instrument", response_model=ResponseStatus)
async def create_instrument(request: InstrumentSharedModel, _:None = Depends(verify_admin_api_key)):
    try:
        job = await instruments_client("add_instrument", AddInstrumentRequest(instrument=request))
        if job is None:
            raise ValueError("Job is None")
        return ResponseStatus(success=True)
    except Exception as e:
        return ResponseStatus(success=False)


@router.delete("/instrument/{ticker}", response_model=ResponseStatus, tags=["user"])
async def delete_instrument(ticker: str, _:None = Depends(verify_admin_api_key)):
    try:
        job = await instruments_client("delete_instrument", DeleteInstrumentRequest(ticker=ticker))
        if job is None:
            raise ValueError("Job is None")
        return ResponseStatus(success=True)
    except Exception as e:
        return ResponseStatus(success=False)


@router.post("/balance/deposit", response_model=ResponseStatus, tags=["balance"])
async def deposit(request: DepositRequest, _:None = Depends(verify_admin_api_key)):
    job = await users_client("deposit", request)
    if job is None:
        raise ValueError("Job is None")
    try:
        await job.result()
        return ResponseStatus(success=True)
    except Exception as e:
        return ResponseStatus(success=False)


@router.post("/balance/withdraw", response_model=ResponseStatus, tags=["balance"])
async def withdraw(request: WithdrawRequest, _:None = Depends(verify_admin_api_key)):
    job = await users_client("withdraw", request)
    if job is None:
        raise ValueError("Job is None")
    try:
        await job.result()
        return ResponseStatus(success=True)
    except Exception as e:
        return ResponseStatus(success=False)