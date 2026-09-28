class UserIDRequiredError(Exception):
    def __init__(self, message: str = "User ID is required"):
        super().__init__(message)


class UserNotFoundError(Exception):
    def __init__(self, message: str = "User not found"):
        super().__init__(message)


class InvalidUserNameError(Exception):
    def __init__(self, message: str = "Invalid user name"):
        super().__init__(message)


class InvalidUserEmailError(Exception):
    def __init__(self, message: str = "Invalid user email"):
        super().__init__(message)


class InvalidUserPasswordError(Exception):
    def __init__(self, message: str = "Invalid user password"):
        super().__init__(message)


class InvalidUserRoleError(Exception):
    def __init__(self, message: str = "Invalid user role"):
        super().__init__(message)


class ExistingEmailError(Exception):
    def __init__(self, message: str = "Email already exists. Please use another email address."):
        super().__init__(message)


class UserOrganizationMismatchError(Exception):
    def __init__(self, message: str = "The user does not belong to that organization."):
        super().__init__(message)


class UserInUseError(Exception):
    def __init__(self, message: str = "The user cannot be deleted because related records exist."):
        super().__init__(message)
