from fastapi import APIRouter, Depends, HTTPException
from microkit import MicroKitClient
from ..config import RedisConfig, ApiServiceConfig
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
from ..logging import get_logger, log_action
from uuid import UUID
import time
from ..services.token import verify_user_api_key

router = APIRouter(prefix="/order", tags=["order"])
orders_client = MicroKitClient(RedisConfig.REDIS_SETTINGS, "Orders")
logger = get_logger("order")


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
    start = time.time()
    job = await orders_client(
        "create_order", CreateOrderRequest(body=request, user_id=user_id)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        response: CreateOrderResponse = await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
        result = "200 (OK)"
        return CreateOrderAPIResponse(success=True, order_id=response.order_id)
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
    except OrdersCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        if isinstance(request, LimitOrderBody):
            order_type = "LIMIT"
            price = str(request.price)
        else:
            order_type = "MARKET"
            price = ""
        identifier = f"\ntype: {order_type} {request.direction.value}\nticker: {request.ticker}\namount: {request.qty}\nprice: {price}\nuser: {user_id}"
        log_action("CREATE ORDER", identifier, result, duration, logger)


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
    start = time.time()
    job = await orders_client("list_orders", ListOrdersRequest(user_id=user_id))
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        result = "200 (OK)"
        return await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
    except UserNotFoundError:
        result = "404 (User Not Found)"
        raise HTTPException(status_code=404, detail="User not found")
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        log_action("LIST ORDERS", str(user_id), result, duration, logger)


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
    start = time.time()
    job = await orders_client(
        "get_order", GetOrderRequest(user_id=user_id, order_id=order_id)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        result = "200 (OK)"
        return await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
    except OrderNotFoundError:
        result = "404 (Order Not Found)"
        raise HTTPException(status_code=404, detail="Order not found")
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        log_action("GET ORDER", str(order_id), result, duration, logger)


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
    start = time.time()
    job = await orders_client(
        "cancel_order", CancelOrderRequest(user_id=user_id, order_id=order_id)
    )
    if job is None:
        raise HTTPException(500, "Cannot create job")
    try:
        await job.result(timeout=10, poll_delay=ApiServiceConfig.DEFAULT_POLL_DELAY)
        result = "200 (OK)"
        return ResponseStatus(success=True)
    except OrderNotFoundError:
        result = "404 (Order Not Found)"
        raise HTTPException(status_code=404, detail="Order not found")
    except asyncio.TimeoutError:
        result = "408 (Request Timeout)"
        raise HTTPException(status_code=408, detail="Request Timeout")
    except OrdersCriticalError as e:
        result = "500 (Critical Error)"
        raise HTTPException(status_code=500, detail=e.message)
    finally:
        duration = time.time() - start
        log_action("CANCEL ORDER", str(order_id), result, duration, logger)
