from fastapi import APIRouter
from app.routes import organizations, customers

api_router = APIRouter()

api_router.include_router(organizations.router)
api_router.include_router(customers.router)