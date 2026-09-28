from fastapi import APIRouter
from app.routes import organizations, customers, conversation, messages

api_router = APIRouter()

api_router.include_router(organizations.router)
api_router.include_router(customers.router)
api_router.include_router(conversation.router)
api_router.include_router(messages.router)
