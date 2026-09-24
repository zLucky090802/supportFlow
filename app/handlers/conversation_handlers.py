from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.exceptions import conversation_exceptions

def register_conversation_handlers(app:FastAPI):
    @app.exception_handler(
        conversation_exceptions.ConversationIdRequiered
    )
    async def conversation_id_required(
        request:Request,
        exc: conversation_exceptions.ConversationIdRequiered
    ):
        return JSONResponse(
            status_code=400,
            content={
                'success':False,
                'message':str(exc),
                'data': None
            }
        )
    
    @app.exception_handler(
        conversation_exceptions.ConversationNotFound
    )
    async def conversation_not_found(
        request:Request,
        exc:conversation_exceptions.ConversationNotFound
    ):
        return JSONResponse(
            status_code=404,
            content={
                'success':False,
                'message':str(exc),
                'data': None
            }
        )
    
    @app.exception_handler(
        conversation_exceptions.InvalidConversationStatusError
    )
    async def invalid_conversation_status_error(
        request:Request,
        exc: conversation_exceptions.InvalidConversationStatusError
    ):
        return JSONResponse(
            status_code=400,
            content={
                'success':False,
                'message':str(exc),
                'data': None
            }
        )