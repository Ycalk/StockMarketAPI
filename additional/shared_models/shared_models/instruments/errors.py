class CriticalError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"CriticalError: {self.message}"

class InstrumentNotFoundError(Exception):
    def __init__(self, ticker: str):
        msg = f"Instrument with ticker {ticker} not found."
        super().__init__(msg)
        self.message = msg
    
    def __str__(self):
        return f"InstrumentNotFound: {self.message}"

class InstrumentAlreadyExistsError(Exception):
    def __init__(self, ticker: str):
        msg = f"Instrument with ticker {ticker} already exists."
        super().__init__(msg)
        self.message = msg
    
    def __str__(self):
        return f"InstrumentAlreadyExists: {self.message}"