from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import message_exceptions


def register_message_handlers(app: FastAPI):
    @app.exception_handler(message_exceptions.MessageIDRequiredError)
    async def message_id_required(
        request: Request,
        exc: message_exceptions.MessageIDRequiredError,
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(message_exceptions.MessageNotFoundError)
    async def message_not_found(
        request: Request,
        exc: message_exceptions.MessageNotFoundError,
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(message_exceptions.InvalidMessageContentError)
    async def invalid_message_content(
        request: Request,
        exc: message_exceptions.InvalidMessageContentError,
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )

    @app.exception_handler(message_exceptions.InvalidMessageSenderError)
    async def invalid_message_sender(
        request: Request,
        exc: message_exceptions.InvalidMessageSenderError,
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(exc), "data": None},
        )
