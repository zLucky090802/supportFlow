from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import organization_exceptions

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(
        organization_exceptions.OrganizationNotFoundError
    )
    async def organization_not_found_handler(
        request: Request,
        exc: organization_exceptions.OrganizationNotFoundError
    ):
        return JSONResponse(
            status_code=404,
            content={
                'success': False,
                'message': str(exc),
                'data':None
            }
        )
        
    @app.exception_handler(
        organization_exceptions.InvalidOrganizationNameError
    )
    async def invalid_organization_name(
        request: Request,
        exc: organization_exceptions.InvalidOrganizationNameError
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
        organization_exceptions.ExistingEmailError
    )
    async def existing_email_error(
        request: Request,
        exc: organization_exceptions.ExistingEmailError
    ):
        return JSONResponse(
            status_code=409,
            content={
                'success': False,
                'message': str(exc),
                'data':None
            }
        )
        
    @app.exception_handler(
        organization_exceptions.EmailRequiredError
    )
    async def email_required_handler(
        request: Request,
        exc: organization_exceptions.EmailRequiredError
    ):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(exc),
                "data": None
            }
        )

    @app.exception_handler(
        organization_exceptions.NameRequiredError
    )
    async def name_required_handler(
        request: Request,
        exc: organization_exceptions.NameRequiredError
    ):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(exc),
                "data": None
            }
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request,
        exc: SQLAlchemyError
    ):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "An unexpected database error occurred",
                "data": None
            }
        )
        