class AuthenticationError(Exception):
    def __init__(self, message: str = "Invalid authentication credentials"):
        super().__init__(message)


class PermissionDeniedError(Exception):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message)


class AuthConfigurationError(Exception):
    def __init__(self):
        super().__init__("Authentication is temporarily unavailable")


class ResourceNotFoundError(Exception):
    def __init__(self):
        super().__init__("Resource not found")
