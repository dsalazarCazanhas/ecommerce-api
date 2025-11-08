from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel

from src.models.base import BaseModel
from src.models.cart import Product


class OrderStatus(str):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class Order(SQLModel, BaseModel, table=True):
    __tablename__ = "order"

    user_id: Optional[int] = Field(foreign_key="user.id")
    total_amount: float = Field(default=0, ge=0)
    currency: str = Field(default="usd")
    status: str = Field(default=OrderStatus.PENDING)

    stripe_session_id: Optional[str] = Field(default=None, index=True)
    stripe_payment_intent_id: Optional[str] = Field(default=None, index=True)

    items: List["OrderItem"] = Relationship(back_populates="order")
    payment: Optional["Payment"] = Relationship(back_populates="order")


class OrderItem(SQLModel, BaseModel, table=True):
    __tablename__ = "order_item"

    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    quantity: int = Field(default=1, ge=1)
    price_at_time: float = Field(default=0, ge=0)

    order: Optional[Order] = Relationship(back_populates="items")
    product: Optional[Product] = Relationship()


class Payment(SQLModel, BaseModel, table=True):
    __tablename__ = "payment"

    order_id: int = Field(foreign_key="order.id")

    stripe_payment_intent_id: Optional[str] = Field(default=None, index=True)
    stripe_session_id: Optional[str] = Field(default=None, index=True)
    amount: float = Field(default=0, ge=0)
    currency: str = Field(default="usd")
    status: str = Field(default="pending")

    order: Optional[Order] = Relationship(back_populates="payment")
