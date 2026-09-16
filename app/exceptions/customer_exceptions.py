class CustomerNotFoundError(Exception):
    def __init__(self, message: str = 'Customer not found'):
        super().__init__(message)
class NameRequiredError(Exception):
    def __init__(self, message: str = 'Name is required'):
        super().__init__(message)
class EmailRequiredError(Exception):
    def __init__(self, message: str = 'Email is required'):
        super().__init__(message)
class OrganizationIDRequiredError(Exception):
    def __init__(self, message: str = 'Organization ID is required'):
        super().__init__(message)

class CustomerIDRequiredError(Exception):
    def __init__(self, message: str = 'Customer ID is required'):
        super().__init__(message)
        
class ExistingEmailError(Exception):
    def __init__(self, message: str = "Email already exists. Please use another email address."):
        super().__init__(message)
        