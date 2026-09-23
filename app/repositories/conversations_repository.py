from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.generated_models import Conversations
from datetime import datetime

def get_conversations(db:Session):
    stmt = select(Conversations)
    
    return db.scalars(stmt).all()

def get_conversation_by_id(db:Session, conversation_id:str):
    stmt = (select(Conversations).where(Conversations.id == conversation_id))
    
    return db.scalar(stmt)
    
    
def get_conversations_by_organization_id(db:Session, organization_id:str):
   stmt = (
       select(Conversations)
       .where(Conversations.organization_id == organization_id)
   ) 
   
   return db.scalar(stmt)

def get_conversation_by_customer_id(db:Session, customer_id:str):
   stmt=(
       select(Conversations)
       .where(Conversations.customer_id == customer_id)
    ) 
   
   return db.scalar(stmt)
   
   
def create_conversation(db:Session,organization_id:str, customer_id:str, status:str):
   try:
       new_conversation = Conversations(
           organization_id= organization_id,
           customer_id= customer_id,
           status= status
       )
       
       db.add()
       db.commit()
       db.refresh(new_conversation)
    
   except SQLAlchemyError:
       db.rollback()
       raise 
   

def update_conversation(db: Session, conversation_id:str, status:str, resolved_at: datetime | None):
   try:
        conversation = db.get(
            Conversations,
            conversation_id
        )

        if conversation is None:
            return None

        stmt = (
            update(Conversations)
            .where(Conversations.id == conversation_id)
            .values(
                status=status,
                resolved_at=resolved_at,
                updated_at=func.current_timestamp()
            )
        )

        db.execute(stmt)
        db.commit()
        db.refresh(conversation)

        return conversation

    except SQLAlchemyError:
        db.rollback()
        raise