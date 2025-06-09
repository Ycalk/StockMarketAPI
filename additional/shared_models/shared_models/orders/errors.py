class CriticalError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"CriticalError: {self.message}"


class OrderNotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"OrderNotFoundError: {self.message}"


class CannotCancelOrderError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"CannotCancelOrderError: {self.message}"
