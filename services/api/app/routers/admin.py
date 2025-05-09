from fastapi import APIRouter, HTTPException
from microkit import MicroKitClient
from ..config import RedisConfig
from ..models.error import ErrorResponse
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
import asyncio
from uuid import UUID
from shared_models.users.errors import CriticalError as UserCriticalError
from shared_models.instruments.errors import CriticalError as InstrumentCriticalError
from shared_models.users.errors import UserNotFoundError


router = APIRouter(prefix="/admin", tags=["admin"])
instruments_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Instruments")
users_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Users")


@router.delete(
    "/user/{user_id}",
    response_model=UserAPIModel,
    responses={
        500: {"model": ErrorResponse},
        408: {"model": ErrorResponse},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def delete_user(user_id: UUID, _: None = Depends(verify_admin_api_key)):
    job = await users_client("delete_user", DeleteUserRequest(id=user_id))
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        model: DeleteUserResponse = await job.result(timeout=10)
        return UserAPIModel(**model.user.model_dump())
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except UserCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post(
    "/instrument",
    response_model=ResponseStatus,
    responses={500: {"model": ErrorResponse}, 408: {"model": ErrorResponse}},
)
async def create_instrument(
    request: InstrumentSharedModel, _: None = Depends(verify_admin_api_key)
):
    job = await instruments_client(
        "add_instrument", AddInstrumentRequest(instrument=request)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10)
        return ResponseStatus(success=True)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except InstrumentCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception:
        return ResponseStatus(success=False)


@router.delete(
    "/instrument/{ticker}",
    response_model=ResponseStatus,
    tags=["user"],
    responses={500: {"model": ErrorResponse}, 408: {"model": ErrorResponse}},
)
async def delete_instrument(ticker: str, _: None = Depends(verify_admin_api_key)):
    job = await instruments_client(
        "delete_instrument", DeleteInstrumentRequest(ticker=ticker)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10)
        return ResponseStatus(success=True)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except InstrumentCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception:
        return ResponseStatus(success=False)


@router.post(
    "/balance/deposit",
    response_model=ResponseStatus,
    tags=["balance"],
    responses={500: {"model": ErrorResponse}, 408: {"model": ErrorResponse}},
)
async def deposit(request: DepositRequest, _: None = Depends(verify_admin_api_key)):
    job = await users_client("deposit", request)
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10)
        return ResponseStatus(success=True)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except UserCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception:
        return ResponseStatus(success=False)


@router.post(
    "/balance/withdraw",
    response_model=ResponseStatus,
    tags=["balance"],
    responses={500: {"model": ErrorResponse}, 408: {"model": ErrorResponse}},
)
async def withdraw(request: WithdrawRequest, _: None = Depends(verify_admin_api_key)):
    job = await users_client("withdraw", request)
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10)
        return ResponseStatus(success=True)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except UserCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception:
        return ResponseStatus(success=False)
