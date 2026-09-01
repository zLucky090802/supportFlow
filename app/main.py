from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter

load_dotenv()

app = FastAPI(title='supportFlow')
router = APIRouter()

@router.get('/health')
def get_health():
    return {
        'status':'ok'
    }
    


app.include_router(router)