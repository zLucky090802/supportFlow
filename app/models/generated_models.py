from typing import Optional
import datetime
import decimal
import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    DECIMAL,
    Date,
    Enum,
    ForeignKeyConstraint,
    Index,
    String,
    TIMESTAMP,
    Text,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


class DocumentsStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class MessagesSenderType(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    AI = "AI"
    AGENT = "AGENT"


class Organizations(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(50),
    )

    customers: Mapped[list["Customers"]] = relationship(
        "Customers",
        back_populates="organization",
    )

    documents: Mapped[list["Documents"]] = relationship(
        "Documents",
        back_populates="organization",
    )

    users: Mapped[list["Users"]] = relationship(
        "Users",
        back_populates="organization",
    )

    conversations: Mapped[list["Conversations"]] = relationship(
        "Conversations",
        back_populates="organization",
    )

    orders: Mapped[list["Orders"]] = relationship(
        "Orders",
        back_populates="organization",
    )


class Customers(Base):
    __tablename__ = "customers"

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_customers_organization_id",
        ),
        Index(
            "idx_customers_email",
            "email",
            unique=True,
        ),
        Index(
            "idx_customers_organization_id",
            "organization_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    organization_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    organization: Mapped["Organizations"] = relationship(
        "Organizations",
        back_populates="customers",
    )

    conversations: Mapped[list["Conversations"]] = relationship(
        "Conversations",
        back_populates="customer",
    )

    orders: Mapped[list["Orders"]] = relationship(
        "Orders",
        back_populates="customer",
    )


class Documents(Base):
    __tablename__ = "documents"

    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_documents_organization",
        ),
        Index(
            "idx_documents_organization_id",
            "organization_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    status: Mapped[DocumentsStatus] = mapped_column(
        Enum(
            DocumentsStatus,
            values_callable=lambda cls: [
                member.value for member in cls
            ],
        ),
        nullable=False,
        server_default=text("'UPLOADED'"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    organization: Mapped["Organizations"] = relationship(
        "Organizations",
        back_populates="documents",
    )


class Users(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "char_length(password_hash) >= 5",
            name="min_password_length",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_users_organization_id",
        ),
        Index(
            "idx_users_email",
            "email",
            unique=True,
        ),
        Index(
            "idx_users_organization_id",
            "organization_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    organization_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        "create_at",
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    organization: Mapped["Organizations"] = relationship(
        "Organizations",
        back_populates="users",
    )

    assigned_conversations: Mapped[list["Conversations"]] = relationship(
        "Conversations",
        back_populates="assigned_agent",
    )


class Conversations(Base):
    __tablename__ = "conversations"

    __table_args__ = (
        ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_conversations_customer_id",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_conversations_organization_id",
        ),
        ForeignKeyConstraint(
            ["assigned_agent_id"],
            ["users.id"],
            name="fk_conversations_assigned_agent_id",
        ),
        Index(
            "idx_conversations_organization_id",
            "organization_id",
        ),
        Index(
            "idx_conversations_customer_id",
            "customer_id",
        ),
        Index(
            "idx_conversations_assigned_agent_id",
            "assigned_agent_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    organization_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    customer_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    assigned_agent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    resolved_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP,
        nullable=True,
    )

    customer: Mapped["Customers"] = relationship(
        "Customers",
        back_populates="conversations",
    )

    organization: Mapped["Organizations"] = relationship(
        "Organizations",
        back_populates="conversations",
    )

    assigned_agent: Mapped[Optional["Users"]] = relationship(
        "Users",
        back_populates="assigned_conversations",
    )

    messages: Mapped[list["Messages"]] = relationship(
        "Messages",
        back_populates="conversation",
    )


class Orders(Base):
    __tablename__ = "orders"

    __table_args__ = (
        ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_orders_customer",
        ),
        ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_orders_organization",
        ),
        Index(
            "idx_orders_customer_id",
            "customer_id",
        ),
        Index(
            "idx_orders_organization_id",
            "organization_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    order_number: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        default=generate_uuid,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    estimated_delivery: Mapped[datetime.date] = mapped_column(
        Date,
        nullable=False,
    )

    total: Mapped[decimal.Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
    )

    organization_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    customer_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    customer: Mapped["Customers"] = relationship(
        "Customers",
        back_populates="orders",
    )

    organization: Mapped["Organizations"] = relationship(
        "Organizations",
        back_populates="orders",
    )


class Messages(Base):
    __tablename__ = "messages"

    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_messages_conversation_id",
        ),
        Index(
            "idx_messages_conversation_id",
            "conversation_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    conversation_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    sender_type: Mapped[MessagesSenderType] = mapped_column(
        Enum(
            MessagesSenderType,
            values_callable=lambda cls: [
                member.value for member in cls
            ],
        ),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    sender_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )

    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    conversation: Mapped["Conversations"] = relationship(
        "Conversations",
        back_populates="messages",
    )
