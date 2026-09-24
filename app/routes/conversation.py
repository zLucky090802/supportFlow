from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.conversations import(
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    ConversationStatus,
    ConversationUpdate
)
from app.services import conversations as conversation_service

router = APIRouter(
    prefix='/conversations',
     tags=['Conversations']
)

@router.get(
    '',
    status_code=status.HTTP_200_OK,
    response_model=ConversationListResponse
)
def get_conversations(
    db:Session = Depends(get_db)
):
    conversations = conversation_service.get_conversations(db=db)
    
    return {
        'success':True,
        'message': 'Conversations retrived successfully',
        'data': conversations
    }
    
@router.get(
    '/{conversation_id}',
    status_code=status.HTTP_200_CREATED,
    response_model=ConversationDetailResponse
)
def get_conversation(
    conversation_id:str,
    db:Session = Depends(get_db),
    
):
    conversation = conversation_service.get_conversation_by_id(db=db, conversation_id=conversation_id)
    
    return {
        'success':True,
        'message': 'Conversation retrived successfully',
        'data': conversation
    }
    
@router.get(
    '/{organization_id}',
    status_code=status.HTTP_200_OK,
    response_model= ConversationDetailResponse
)
def get_conversation_by_organization_id(
    organization_id:str,
    db: Session = Depends(get_db)
):
    conversation = conversation_service.get_conversation_by_organization_id(db=db, organization_id=organization_id)
    
    return {
        'success':True,
        'message': 'Conversation retrived successfully',
        'data': conversation
    }
    

@router.get(
    '/{customer_id}',
    status_code=status.HTTP_200_OK,
    response_model=ConversationDetailResponse
)
def get_conversation_by_customer_id(
    customer_id: str,
    db: Session = Depends(get_db)
):
    conversation = conversation_service.get_conversation_by_customer_id(db=db, customer_id=customer_id)
    
    return {
        'success':True,
        'message': 'Conversation retrived successfully',
        'data': conversation
    }
    
@router.post(
    '',
    status_code=status.HTTP_201_CREATED,
    response_model= ConversationDetailResponse
)
def create_conversation(
    data: ConversationCreate,
    db:Session
):
    new_conversation = conversation_service.create_conversation(db=db, conversation=data)
    
    return {
        'success':True,
        'message': 'Conversation created successfully',
        'data': new_conversation
    }
    
    
@router.patch(
    '/{conversation_id}',
    status_code=status.HTTP_200_OK,
    response_model= ConversationDetailResponse
)
def update_conversation(
    data: ConversationUpdate,
    conversation_id:str,
    db: Session = Depends(get_db)
):
    updated = conversation_service.update_conversation(db=db, data=data, conversation_id=conversation_id)
    
    return {
        'success':True,
        'message': 'Conversation updated successfully',
        'data': updated
    }
