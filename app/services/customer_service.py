from sqlalchemy.orm import Session
from app.repositories import customers_repository
from app.exceptions import customer_exceptions, organization_exceptions
from app.schemas.customers import (
    CustomerCreate,
    CustomerUpdate
)
from app.repositories import organization_repository



def get_customers(db:Session):
    customers = customers_repository.get_customers(db=db)
    
    return customers

def get_customer_by_id(db:Session, customer_id:str):
    
    customer = customers_repository.get_customer_by_id(db=db, customer_id=customer_id)
    
    if customer is None:
        raise customer_exceptions.CustomerNotFoundError()
    
    return customer

def get_customers_by_organization_id(db:Session, organization_id:str):
    organization = organization_repository.get_organization_by_id(
        db=db, 
        organization_id=organization_id
    )
    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()
    

    
    
    return customers_repository.get_customers_by_organization_id(db=db, organization_id=organization_id)

def create_customer(db:Session, customer: CustomerCreate):
    organization = organization_repository.get_organization_by_id(
        db=db,
        organization_id=customer.organization_id
    )
    
    if organization is None:
        raise organization_exceptions.OrganizationNotFoundError()
    
    name = customer.name.strip()
    email = str(customer.email).strip().lower()
    
    if not name:
        raise customer_exceptions.InvalidCustomerNameError()
    
    
    

    existing = customers_repository.get_customer_by_email(
        db=db,
        customer_email=email
    )

    if existing is not None:
        raise customer_exceptions.ExistingEmailError()
    
    
    return customers_repository.create_customer(
        db=db,
        organization_id=customer.organization_id,
        name=name,
        email=email
    )

def update_customer(
    db: Session,
    customer: CustomerUpdate,
    customer_id: str
):
    existing = customers_repository.get_customer_by_id(
        db=db,
        customer_id=customer_id
    )

    if existing is None:
        raise customer_exceptions.CustomerNotFoundError()

    # Name
    if customer.name is not None:
        name = customer.name.strip()

        if not name:
            raise customer_exceptions.InvalidCustomerNameError()
    else:
        name = existing.name

    # Email
    if customer.email is not None:
        email = str(customer.email).strip().lower()

        email_exist = customers_repository.get_customer_by_email(
            db=db,
            customer_email=email
        )

        if (
            email_exist is not None
            and email_exist.id != customer_id
        ):
            raise customer_exceptions.ExistingEmailError()
    else:
        email = existing.email

    return customers_repository.update_customer(
        db=db,
        customer_id=customer_id,
        name=name,
        email=email
    )


def delete_customer(db:Session, customer_id:str ):

    
    existing = customers_repository.get_customer_by_id(db=db, customer_id=customer_id)
    
    if existing is None:
        raise customer_exceptions.CustomerNotFoundError()
    
    return customers_repository.delete_customer(db=db, customer_id=customer_id)