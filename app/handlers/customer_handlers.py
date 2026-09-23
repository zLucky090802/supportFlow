from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import customer_exceptions


def register_customer_handlers(app: FastAPI):
    @app.exception_handler(
        customer_exceptions.CustomerNotFoundError
    )
    async def customer_notr_found_handler(
        request: Request,
        exc: customer_exceptions.CustomerNotFoundError
    ):
        return JSONResponse(
            status_code=404,
            content={
                'success': False,
                'message':str(exc),
                'data': None
            }
        )
        
    @app.exception_handler(
        customer_exceptions.CustomerIDRequiredError
    )
    async def customer_id_required(
        request: Request,
        exc: customer_exceptions.CustomerIDRequiredError
    ):
        return JSONResponse(
            status_code=400,
            content={
                'success':False,
                'message':str(exc),
                'data':None
            }
            
        )
        
    @app.exception_handler(
        customer_exceptions.EmailRequiredError
    )
    async def customer_email_requiered(
        request:Request,
        exc:customer_exceptions.EmailRequiredError
    ):
        return JSONResponse(
            status_code=400,
            content={
                'success': False,
                'message': str(exc),
                'data':None
            }
        )
        
        
    @app.exception_handler(
        customer_exceptions.NameRequiredError
    )
    async def customer_name_requiered(
        request:Request,
        exc:customer_exceptions.NameRequiredError
    ):
        return JSONResponse(
            status_code=400,
            content={
                'success': False,
                'message': str(exc),
                'data':None
            }
        )
        
        
        
    @app.exception_handler(
        customer_exceptions.OrganizationIDRequiredError
    )
    async def customer_organization_id_requiered(
        request:Request,
        exc:customer_exceptions.OrganizationIDRequiredError
    ):
        return JSONResponse(
            status_code=400,
            content={
                'success': False,
                'message': str(exc),
                'data':None
            }
        )
        
        
    @app.exception_handler(
        customer_exceptions.ExistingEmailError
    )
    async def customer_existing_email(
        request:Request,
        exc:customer_exceptions.ExistingEmailError
    ):
        return JSONResponse(
            status_code=409,
            content={
                'success': False,
                'message': str(exc),
                'data':None
            }
        )