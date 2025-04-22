import asyncio
from functools import wraps
import inspect
from typing import Any, Callable


def service_method(func: Callable):
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(f"Function {func.__name__} must be a coroutine function")

    sig = inspect.signature(func)
    if len(sig.parameters) < 2:
        raise TypeError(
            f"Function {func.__name__} must have at least two parameters: self and redis"
        )

    @wraps(func)
    async def wrapper(ctx: dict[str, Any], *args, **kwargs):
        self = ctx["self"]
        redis = ctx["redis"]
        return await func(self, redis, *args, **kwargs)

    wrapper.is_service_method = True  # type: ignore
    return staticmethod(wrapper)
