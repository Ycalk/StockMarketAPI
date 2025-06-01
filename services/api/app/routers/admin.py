import time
from fastapi import APIRouter, HTTPException
from microkit import MicroKitClient
from ..config import RedisConfig, ApiServiceConfig
from ..models.error import ErrorResponse
from shared_models.instruments.add_instrument import AddInstrumentRequest
from shared_models.instruments import Instrument as InstrumentSharedModel
from shared_models.instruments.delete_instrument import DeleteInstrumentRequest
from shared_models.users.delete_user import DeleteUserRequest, DeleteUserResponse
from shared_models.users.deposit import DepositRequest
from shared_models.users.withdraw import WithdrawRequest
from ..models.user import User as UserAPIModel
from ..logging import get_logger, log_action
from ..models.response_status import ResponseStatus
from ..services.token import verify_admin_api_key
from fastapi import Depends
import asyncio
from uuid import UUID
from shared_models.users.errors import CriticalError as UserCriticalError
from shared_models.instruments.errors import (
    CriticalError as InstrumentCriticalError,
    InstrumentAlreadyExistsError,
    InstrumentNotFoundError,
)
from shared_models.users.errors import UserNotFoundError, InsufficientFundsError


router = APIRouter(prefix="/admin", tags=["admin"])
instruments_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Instruments")
users_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Users")
logger = get_logger("admin")


@router.delete(
    "/user/{user_id}",
    response_model=UserAPIModel,
    tags=["user"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def delete_user(user_id: UUID, _: None = Depends(verify_admin_api_key)):
    start = time.time()
    job = await users_client("delete_user", DeleteUserRequest(id=user_id))
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        model: DeleteUserResponse = await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
        result = "200 (OK)"
        return UserAPIModel(**model.user.model_dump())
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except UserNotFoundError as e:
        result = "404 (User Not Found)"
        raise HTTPException(status_code=404, detail=e.message)
    except UserCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        log_action("DELETE USER", str(user_id), result, duration, logger)


@router.post(
    "/instrument",
    response_model=ResponseStatus,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        409: {"model": ErrorResponse, "description": "Instrument already exists"},
    },
)
async def create_instrument(
    request: InstrumentSharedModel, _: None = Depends(verify_admin_api_key)
):
    start = time.time()
    job = await instruments_client(
        "add_instrument", AddInstrumentRequest(instrument=request)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
        result = "200 (OK)"
        return ResponseStatus(success=True)
    except InstrumentAlreadyExistsError:
        result = "409 (Instrument Already Exists)"
        raise HTTPException(status_code=409, detail="Instrument already exists")
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except InstrumentCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        log_action("CREATE INSTRUMENT", request.ticker, result, duration, logger)


@router.delete(
    "/instrument/{ticker}",
    response_model=ResponseStatus,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "Instrument not found"},
    },
)
async def delete_instrument(ticker: str, _: None = Depends(verify_admin_api_key)):
    start = time.time()
    job = await instruments_client(
        "delete_instrument", DeleteInstrumentRequest(ticker=ticker)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
        result = "200 (OK)"
        return ResponseStatus(success=True)
    except InstrumentNotFoundError:
        result = "404 (Instrument Not Found)"
        raise HTTPException(status_code=404, detail="Instrument not found")
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except InstrumentCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        log_action("DELETE INSTRUMENT", ticker, result, duration, logger)


@router.post(
    "/balance/deposit",
    response_model=ResponseStatus,
    tags=["balance"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "User or Instrument not found"},
    },
)
async def deposit(request: DepositRequest, _: None = Depends(verify_admin_api_key)):
    start = time.time()
    job = await users_client("deposit", request)
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
        result = "200 (OK)"
        return ResponseStatus(success=True)
    except UserNotFoundError:
        result = "404 (User Not Found)"
        raise HTTPException(status_code=404, detail="User not found")
    except InstrumentNotFoundError:
        result = "404 (Instrument Not Found)"
        raise HTTPException(status_code=404, detail="Instrument not found")
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except UserCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        identifier = f"{request.amount} {request.ticker} to {request.user_id}"
        log_action("DEPOSIT", identifier, result, duration, logger)


@router.post(
    "/balance/withdraw",
    response_model=ResponseStatus,
    tags=["balance"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "User or Instrument not found"},
        403: {"model": ErrorResponse, "description": "Insufficient funds"},
    },
)
async def withdraw(request: WithdrawRequest, _: None = Depends(verify_admin_api_key)):
    start = time.time()
    job = await users_client("withdraw", request)
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
        result = "200 (OK)"
        return ResponseStatus(success=True)
    except UserNotFoundError:
        result = "404 (User Not Found)"
        raise HTTPException(status_code=404, detail="User not found")
    except InstrumentNotFoundError:
        result = "404 (Instrument Not Found)"
        raise HTTPException(status_code=404, detail="Instrument not found")
    except InsufficientFundsError:
        result = "403 (Insufficient Funds)"
        raise HTTPException(status_code=403, detail="Insufficient funds")
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except UserCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        identifier = f"{request.amount} {request.ticker} from {request.user_id}"
        log_action("WITHDRAW", identifier, result, duration, logger)
