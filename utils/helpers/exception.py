class CustomException(Exception):
    """custom exception class that can be used to raise exceptions with custom messages"""
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message
