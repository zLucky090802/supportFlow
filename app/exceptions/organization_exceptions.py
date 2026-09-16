class OrganizationNotFoundError(Exception):
    def __init__(self, message: str = 'Organization not found'):
        super().__init__(message)
        
class InvalidOrganizationNameError(Exception):
    def __init__(self, message: str = 'Invalid Organization Name'):
        super().__init__(message)
        
class ExistingEmailError(Exception):
    def __init__(self, message: str = "Email already exists. Please use another email address."):
        super().__init__(message)
        
class EmailRequiredError(Exception):
    def __init__(self, message: str = 'Email is required, please enter a email address'):
        super().__init__(message)
        
class NameRequiredError(Exception):
    def __init__(self, message: str = 'Name is required, please enter a Name'):
        super().__init__(message)