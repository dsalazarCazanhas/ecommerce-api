from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import UUID4
from sqlmodel import Field, Relationship, SQLModel

from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.products import Product


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    """Payment status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Order(BaseModel, table=True):
    __tablename__ = "order"

    user_id: UUID4 = Field(foreign_key="user.id")
    total_amount: float = Field(default=0, ge=0)
    currency: str = Field(default="usd")
    status: OrderStatus = Field(default=OrderStatus.PENDING)

    stripe_session_id: Optional[str] = Field(default=None, index=True)
    stripe_payment_intent_id: Optional[str] = Field(default=None, index=True)

    items: list["OrderItem"] = Relationship(back_populates="order")
    payment: Optional["Payment"] = Relationship(back_populates="order")


class OrderItem(BaseModel, table=True):
    __tablename__ = "order_item"

    order_id: UUID4 = Field(foreign_key="order.id")
    product_id: UUID4 = Field(foreign_key="product.id")
    quantity: int = Field(default=1, ge=1)
    price_at_time: float = Field(default=0, ge=0)

    order: "Order" = Relationship(back_populates="items")
    product: "Product" = Relationship()


class Payment(BaseModel, table=True):
    __tablename__ = "payment"

    order_id: UUID4 = Field(foreign_key="order.id")

    stripe_payment_intent_id: Optional[str] = Field(default=None, index=True)
    stripe_session_id: Optional[str] = Field(default=None, index=True)
    amount: float = Field(default=0, ge=0)
    currency: str = Field(default="usd")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)

    order: "Order" = Relationship(back_populates="payment")


class CheckoutSummary(SQLModel, table=False):
    """Public contract returned by cart checkout and consumed by payment setup."""

    order_id: UUID4
    cart_id: UUID4
    order_status: OrderStatus
    total_amount: float
    currency: str
