from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, Depends
from sqlalchemy import text
from app.db.database import engine
from app.routes.api import api_router
from app.handlers.organization_handlers import register_exception_handlers
from app.handlers.customer_handlers import register_customer_handlers
from app. handlers.conversation_handlers import register_conversation_handlers
from app.handlers.message_handlers import register_message_handlers
from app.handlers.user_handlers import register_user_handlers
from app.handlers.auth_handlers import register_auth_handlers
from app.dependencies.auth import require_roles

load_dotenv()

app = FastAPI(title='supportFlow')

router = APIRouter()

app.include_router(api_router)


@app.get('/health')
def get_health():
    return {
        'status':'ok'
    }
    
@app.get('/db-health', dependencies=[Depends(require_roles("ADMIN"))])
def get_db_health():
    with engine.connect() as connection:
        result = connection.execute(
            text('SELECT 1')
        )
        
        return {
            'database':'connected',
            'result': result.scalar()
        }

app.include_router(router)

register_exception_handlers(app)
register_customer_handlers(app)
register_conversation_handlers(app)
register_message_handlers(app)
register_user_handlers(app)
register_auth_handlers(app)
