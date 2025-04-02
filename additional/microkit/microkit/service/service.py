import inspect


class Service:
    def __init__(self) -> None:
        self._functions = []
        for _, method in inspect.getmembers(self, predicate=inspect.iscoroutinefunction):
            if hasattr(method , "is_service_method"):
                self._functions.append(method)
    
    async def init(self) -> None:
        pass
    
    async def shutdown(self) -> None:
        pass