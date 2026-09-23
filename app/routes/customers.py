from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.customers import(
    CustomerCreate,
    CustomerDetailResponse,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
    
)
from app.services import customer_service

router = APIRouter(
    prefix='/customer',
    tags=['Customers']
)

@router.get(
    '',
    status_code=status.HTTP_200_OK,
    response_model=CustomerListResponse
)
def get_customers(
    db: Session = Depends(get_db)
):
    customers = customer_service.get_customers(
        db=db
    )
    
    return {
        'success': True,
        'message': 'Customers retrieved succesfully',
        'data': customers
    }
    
@router.get(
    '/{customer_id}',
    status_code=status.HTTP_200_OK,
    response_model=CustomerDetailResponse
)
def get_customer_by_id(
    customer_id= str,
    db:Session= Depends(get_db),
    
):
    customer = customer_service.get_customer_by_id(db=db, customer_id=customer_id)
    
    return {
        'success': True,
        'message': 'Customer retrived successfully',
        'data': customer
    }
    

@router.get(
    '/organizations/{organization_id}/customers',
    status_code=status.HTTP_200_OK,
    response_model=CustomerListResponse
)
def get_customers_by_organization_id(
    organization_id: str,
    db: Session = Depends(get_db),
    
):
    customers = customer_service.get_customers_by_organization_id(db=db, organization_id=organization_id)
    
    
    return {
        'success': True,
        'message': 'Customers retrieved successfully',
        'data': customers
    }


@router.post(
    '',
    status_code=status.HTTP_201_CREATED,
    response_model=CustomerDetailResponse
)
def create_customer(
    data: CustomerCreate,
    db:Session = Depends(get_db),
    
):
    created = customer_service.create_customer(db=db, customer=data)
    
    return {
        'success': True,
        'message': 'Customer created succesfully',
        'data': created
    }
    

@router.patch(
    '/{customer_id}',
    status_code=status.HTTP_200_OK,
    response_model=CustomerDetailResponse
)
def update_customer(
    data: CustomerUpdate,
    customer_id: str,
    db: Session = Depends(get_db)
):
    updated = customer_service.update_customer(db=db,customer= data, customer_id=customer_id)
    
    return{
        'success':True,
        'message': 'Updated customer succesfuflly',
        'data': updated
    } 
    

@router.delete(
    '/{customer_id}',
    status_code=status.HTTP_204_NO_CONTENT,
 
)
def delete_customer(
    customer_id:str,
    db:Session = Depends (get_db)
):
   customer_service.delete_customer(db=db, customer_id=customer_id)
   
   return Response(
       status_code=status.HTTP_204_NO_CONTENT
   )