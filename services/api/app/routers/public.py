from fastapi import APIRouter, HTTPException
from ..models.public import RegisterUserRequest
from ..models.user import User as UserAPIModel
from ..models.error import ErrorResponse
from microkit.client import MicroKitClient
from ..config import RedisConfig
from shared_models.users.create_user import CreateUserRequest, CreateUserResponse
from shared_models.instruments.get_instruments import GetInstrumentsResponse
import asyncio
from shared_models.users.errors import CriticalError as UserCriticalError
from shared_models.instruments.errors import CriticalError as InstrumentCriticalError
from shared_models.orders.requests.get_orderbook import (
    GetOrderbookRequest,
    GetOrderbookResponse,
)
from shared_models.orders.requests.get_transactions import (
    GetTransactionsRequest,
    GetTransactionsResponse,
)
from shared_models.orders.errors import CriticalError as OrdersCriticalError
from shared_models.instruments.errors import InstrumentNotFoundError


router = APIRouter(prefix="/public", tags=["public"])
users_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Users")
instruments_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Instruments")
orders_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Orders")


@router.post(
    "/register",
    response_model=UserAPIModel,
    responses={500: {"model": ErrorResponse, "description": "Internal Server Error"}, 408: {"model": ErrorResponse, "description": "Request Timeout"}},
)
async def register_user(request: RegisterUserRequest):
    job = await users_client("create_user", CreateUserRequest(**request.model_dump()))
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        model: CreateUserResponse = await job.result(timeout=10)
        return UserAPIModel(**model.user.model_dump())
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except UserCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get(
    "/instrument",
    response_model=GetInstrumentsResponse,
    responses={500: {"model": ErrorResponse, "description": "Internal Server Error"}, 408: {"model": ErrorResponse, "description": "Request Timeout"}},
)
async def get_instruments():
    job = await instruments_client("get_instruments")
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        return await job.result(timeout=10)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except InstrumentCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get(
    "/orderbook/{ticker}",
    response_model=GetOrderbookResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "Orderbook not found"},
    },
)
async def get_orderbook(ticker: str, limit: int = 10):
    job = await orders_client(
        "get_orderbook", GetOrderbookRequest(ticker=ticker, limit=limit)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        return await job.result(timeout=10)
    except InstrumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get(
    "/transactions/{ticker}",
    response_model=GetTransactionsResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "Instrument not found"},
    },
)
async def get_transactions(ticker: str, limit: int = 10):
    job = await orders_client(
        "get_transactions", GetTransactionsRequest(ticker=ticker, limit=limit)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        return await job.result(timeout=10)
    except InstrumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)
