from fastapi import APIRouter, Depends, HTTPException
from microkit import MicroKitClient
from ..config import RedisConfig
from typing import Union
import asyncio
from shared_models.orders.requests.list_orders import (
    ListOrdersRequest,
    ListOrdersResponse,
)
from shared_models.instruments.errors import InstrumentNotFoundError
from shared_models.users.errors import InsufficientFundsError
from shared_models.orders.requests.get_order import GetOrderRequest, GetOrderResponse
from shared_models.orders.errors import OrderNotFoundError
from shared_models.users.errors import UserNotFoundError
from shared_models.orders.requests.cancel_order import CancelOrderRequest
from shared_models.orders.requests.create_order import (
    CreateOrderRequest,
    CreateOrderResponse,
)
from shared_models.orders.errors import CriticalError as OrdersCriticalError
from shared_models.orders.models.orders_bodies import LimitOrderBody, MarketOrderBody
from ..models.create_order import CreateOrderResponse as CreateOrderAPIResponse
from ..models.error import ErrorResponse
from ..models.response_status import ResponseStatus
from uuid import UUID
from ..services.token import verify_user_api_key

router = APIRouter(prefix="/order", tags=["order"])
orders_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Orders")


@router.post(
    "",
    response_model=CreateOrderAPIResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "User or instrument not found"},
        403: {"model": ErrorResponse, "description": "Insufficient funds"},
    },
)
async def create_order(
    request: Union[LimitOrderBody, MarketOrderBody],
    user_id: UUID = Depends(verify_user_api_key),
):
    job = await orders_client(
        "create_order", CreateOrderRequest(body=request, user_id=user_id)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        result: CreateOrderResponse = await job.result(timeout=10)
        return CreateOrderAPIResponse(success=True, order_id=result.order_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except InstrumentNotFoundError:
        raise HTTPException(status_code=404, detail="Instrument not found")
    except InsufficientFundsError:
        raise HTTPException(status_code=403, detail="Insufficient funds")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get(
    "",
    response_model=ListOrdersResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def list_orders(user_id: UUID = Depends(verify_user_api_key)):
    job = await orders_client("list_orders", ListOrdersRequest(user_id=user_id))
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        return await job.result(timeout=10)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get(
    "/{order_id}",
    response_model=GetOrderResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
async def get_order(order_id: UUID, user_id: UUID = Depends(verify_user_api_key)):
    job = await orders_client(
        "get_order", GetOrderRequest(user_id=user_id, order_id=order_id)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        return await job.result(timeout=10)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.delete(
    "/{order_id}",
    response_model=ResponseStatus,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        408: {"model": ErrorResponse, "description": "Request Timeout"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
async def cancel_order(order_id: UUID, user_id: UUID = Depends(verify_user_api_key)):
    job = await orders_client(
        "cancel_order", CancelOrderRequest(user_id=user_id, order_id=order_id)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10)
        return ResponseStatus(success=True)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        raise HTTPException(status_code=500, detail=e.message)
