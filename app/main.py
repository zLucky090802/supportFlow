from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from sqlalchemy import text
from app.db.database import engine
from app.routes.organizations import router as organization_router
from app.handlers.exception_handlers import register_exception_handlers

load_dotenv()

app = FastAPI(title='supportFlow')
register_exception_handlers(app)
router = APIRouter()

app.include_router(organization_router)


@app.get('/health')
def get_health():
    return {
        'status':'ok'
    }
    
@app.get('/db-health')
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