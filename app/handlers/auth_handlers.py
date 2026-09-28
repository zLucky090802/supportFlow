from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.auth_exceptions import (
    AuthenticationError, AuthConfigurationError, PermissionDeniedError,
)


def register_auth_handlers(app: FastAPI) -> None:
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
