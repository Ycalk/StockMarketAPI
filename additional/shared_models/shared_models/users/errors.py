class CriticalError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"CriticalError: {self.message}"


class UserNotFoundError(Exception):
    def __init__(self, user_id: str):
        msg = f"User with ID {user_id} not found."
        super().__init__(msg)
        self.message = msg

    def __str__(self):
        return f"UserNotFoundError: {self.message}"


class InsufficientFundsError(Exception):
    def __init__(self, user_id: str, requested: int, available: int):
        msg = f"User {user_id} has insufficient funds. Requested: {requested}, Available: {available}."
        self.user_id = user_id
        self.requested = requested
        self.available = available
        super().__init__(msg)
        self.message = msg

    def __str__(self):
        return f"InsufficientFundsError: {self.message}"

    def __reduce__(self):
        return (self.__class__, (self.user_id, self.requested, self.available))
