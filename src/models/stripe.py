from pydantic import UUID4, BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import UniqueConstraint
from sqlmodel import Field as SQLField

from src.models.base import BaseModel as ORMBaseModel


class LineItem(BaseModel):
    name: str
    currency: str = "usd"
    amount: int = PydanticField(..., gt=0, description="Amount in cents")
    quantity: int = PydanticField(..., gt=0)


class CheckoutRequest(BaseModel):
    order_id: UUID4
    line_items: list[LineItem]
    success_url: str
    cancel_url: str


class PaymentMethodRequest(BaseModel):
    """Request schema for payment method registration."""

    account_number: str
    routing_number: str
    holder_name: str


class StripeWebhookEvent(ORMBaseModel, table=True):
    """Stores processed Stripe event ids to make webhook handling idempotent."""

    __tablename__ = "stripe_webhook_event"
    __table_args__ = (
        UniqueConstraint("stripe_event_id", name="uq_stripe_webhook_event_id"),
    )

    stripe_event_id: str = SQLField(index=True, min_length=1, max_length=255)
    event_type: str = SQLField(min_length=1, max_length=255)
