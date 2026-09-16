from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.generated_models import Customers


def get_customers(db: Session):
    stmt = select(Customers)

    return db.scalars(stmt).all()


def get_customer_by_id(
    db: Session,
    customer_id: str
):
    stmt = (
        select(Customers)
        .where(Customers.id == customer_id)
    )

    return db.scalar(stmt)


def get_customer_by_email(
    db: Session,
    customer_email: str
):
    stmt = (
        select(Customers)
        .where(Customers.email == customer_email)
    )

    return db.scalar(stmt)


def get_customers_by_organization_id(
    db: Session,
    organization_id: str
):
    stmt = (
        select(Customers)
        .where(
            Customers.organization_id == organization_id
        )
    )

    return db.scalars(stmt).all()


def create_customer(
    db: Session,
    organization_id: str,
    name: str,
    email: str
):
    try:
        customer = Customers(
            organization_id=organization_id,
            name=name,
            email=email
        )

        db.add(customer)
        db.commit()
        db.refresh(customer)

        return customer

    except SQLAlchemyError:
        db.rollback()
        raise


def update_customer(
    db: Session,
    customer_id: str,
    name: str,
    email: str
):
    try:
        stmt = (
            update(Customers)
            .where(Customers.id == customer_id)
            .values(
                name=name,
                email=email
            )
        )

        db.execute(stmt)
        db.commit()

        return get_customer_by_id(
            db=db,
            customer_id=customer_id
        )

    except SQLAlchemyError:
        db.rollback()
        raise


def delete_customer(
    db: Session,
    customer_id: str
):
    try:
        stmt = (
            delete(Customers)
            .where(Customers.id == customer_id)
        )

        result = db.execute(stmt)
        db.commit()

        return result.rowcount > 0

    except SQLAlchemyError:
        db.rollback()
        raise