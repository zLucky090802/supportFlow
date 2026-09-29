from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.auth_exceptions import (
    AuthenticationError, AuthConfigurationError, PermissionDeniedError, ResourceNotFoundError,
)

from app.exceptions.user_exceptions import UserNotFoundError
from app.exceptions.organization_exceptions import OrganizationNotFoundError
from app.exceptions.customer_exceptions import CustomerNotFoundError
from app.exceptions.conversation_exceptions import ConversationNotFound
from app.exceptions.message_exceptions import MessageNotFoundError


def register_auth_handlers(app: FastAPI) -> None:
    # Register last so missing and inaccessible resources have one HTTP contract.
    async def resource_not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Resource not found", "data": None},
        )

    for exception in (
        ResourceNotFoundError, UserNotFoundError, OrganizationNotFoundError,
        CustomerNotFoundError, ConversationNotFound, MessageNotFoundError,
    ):
        app.add_exception_handler(exception, resource_not_found)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic errors can include the original password or other sensitive inputs.
        return JSONResponse(
            status_code=422,
            content={"success": False, "message": "Invalid request data", "data": None},
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error(request: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": str(exc), "data": None},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied(request: Request, exc: PermissionDeniedError) -> JSONResponse:
        return JSONResponse(
            status_code=403, content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(AuthConfigurationError)
    async def configuration_error(request: Request, exc: AuthConfigurationError) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"success": False, "message": str(exc), "data": None},
        )
