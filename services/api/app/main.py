from fastapi import FastAPI
from .routers import admin, balance, order, public
from .config import ApiServiceConfig


app = FastAPI(title=ApiServiceConfig.API_NAME)
app.include_router(public.router, prefix=ApiServiceConfig.BASE_PREFIX)
app.include_router(balance.router, prefix=ApiServiceConfig.BASE_PREFIX)
app.include_router(order.router, prefix=ApiServiceConfig.BASE_PREFIX)
app.include_router(admin.router, prefix=ApiServiceConfig.BASE_PREFIX)

