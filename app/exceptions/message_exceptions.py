class MessageIDRequiredError(Exception):
    def __init__(self, message: str = "Message ID is required"):
        super().__init__(message)


class MessageNotFoundError(Exception):
    def __init__(self, message: str = "Message not found"):
        super().__init__(message)


class InvalidMessageContentError(Exception):
    def __init__(self, message: str = "Message content cannot be empty"):
        super().__init__(message)


class InvalidMessageSenderError(Exception):
    def __init__(self, message: str = "Invalid message sender"):
        super().__init__(message)
