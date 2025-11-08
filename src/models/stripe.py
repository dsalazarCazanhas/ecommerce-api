from pydantic import BaseModel, Field
from typing import List


class LineItem(BaseModel):
    name: str
    currency: str = "usd"
    amount: int = Field(..., gt=0, description="Amount in cents")
    quantity: int = Field(..., gt=0)


class CheckoutRequest(BaseModel):
    line_items: List[LineItem]
    success_url: str
    cancel_url: str


class PaymentMethodRequest(BaseModel):
    account_number: str
    routing_number: str
    holder_name: str
