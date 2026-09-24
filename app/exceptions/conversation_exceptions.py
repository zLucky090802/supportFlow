class ConversationIdRequiered(Exception):
    def __init__(self, message: str = 'Id is required'):
        super().__init__(message)
        
class ConversationNotFound(Exception):
    def __init__(self, message: str = 'Conversation not found'):
        super().__init__(message)
        
class InvalidConversationStatusError(Exception):
    def __init__(self, message: str = 'Invalid conversation status. Please provide a valid status.'):
        super().__init__(message)
        
