from fastapi import APIRouter
from app.routes import organizations, customers, conversation, messages, users, auth

api_router = APIRouter()
api_router.include_router(auth.router)

api_router.include_router(organizations.router)
api_router.include_router(customers.router)
api_router.include_router(conversation.router)
api_router.include_router(messages.router)
api_router.include_router(messages.conversation_router)
api_router.include_router(users.router)
