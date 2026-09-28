from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import user_exceptions


def register_user_handlers(app: FastAPI) -> None:
    @app.exception_handler(user_exceptions.UserIDRequiredError)
    async def user_id_required(
        request: Request,
        exc: user_exceptions.UserIDRequiredError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(user_exceptions.UserNotFoundError)
    async def user_not_found(
        request: Request,
        exc: user_exceptions.UserNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(user_exceptions.InvalidUserNameError)
    async def invalid_user_name(
        request: Request,
        exc: user_exceptions.InvalidUserNameError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(user_exceptions.InvalidUserEmailError)
    async def invalid_user_email(
        request: Request,
        exc: user_exceptions.InvalidUserEmailError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(user_exceptions.InvalidUserPasswordError)
    async def invalid_user_password(
        request: Request,
        exc: user_exceptions.InvalidUserPasswordError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(user_exceptions.InvalidUserRoleError)
    async def invalid_user_role(
        request: Request,
        exc: user_exceptions.InvalidUserRoleError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(user_exceptions.ExistingEmailError)
    async def existing_email(
        request: Request,
        exc: user_exceptions.ExistingEmailError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(user_exceptions.UserOrganizationMismatchError)
    async def user_organization_mismatch(
        request: Request,
        exc: user_exceptions.UserOrganizationMismatchError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(user_exceptions.UserInUseError)
    async def user_in_use(
        request: Request,
        exc: user_exceptions.UserInUseError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"success": False, "message": str(exc), "data": None},
        )
