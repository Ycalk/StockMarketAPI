import inspect


class Service:
    """
    A base class for creating service components in an application. This class is designed to
    automatically collect coroutine methods marked as service methods and provides hooks for
    initialization and shutdown processes.
    Methods
    -------
        init():
            An asynchronous method intended to be overridden for initializing the service.
        shutdown():
            An asynchronous method intended to be overridden for shutting down the service.
    """

    def __init__(self) -> None:
        self._functions = []
        for _, method in inspect.getmembers(
            self, predicate=inspect.iscoroutinefunction
        ):
            if hasattr(method, "is_service_method"):
                self._functions.append(method)

    async def init(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass
