from enum import Enum
from typing import List
from pydantic import UUID4
from sqlmodel import Field, Relationship

from src.models.base import BaseModel
from src.models.products import Product
from src.models.users import User


# === Shopping Cart Models ===
class CartStatus(str, Enum):
    """Estados del usuario"""
    ACTIVE = "active"
    ABANDONED = "abandoned"
    ORDERED = "ordered"

"""Shopping cart and cart item models for e-commerce functionality."""
class CartItem(BaseModel, table=True):
    __tablename__ = "cart_item"

    cart_id: UUID4 = Field(foreign_key="cart.id")
    product_id: UUID4 = Field(foreign_key="product.id")
    quantity: int = Field(default=1, ge=1)
    
    unit_price: float = Field(..., description="Unit price at the time of adding to cart")
    
    cart: "Cart" = Relationship(back_populates="items")
    product: "Product" = Relationship(back_populates="cart_items")

class Cart(BaseModel, table=True):
    __tablename__ = "cart"

    # each cart is associated with a user
    user_id: UUID4 = Field(foreign_key="user.id")
    # cart status: active, ordered, abandoned
    status: CartStatus = Field(default=CartStatus.ACTIVE)
    
    items: List["CartItem"] = Relationship(back_populates="cart")
    user: "User" = Relationship(back_populates="cart")
