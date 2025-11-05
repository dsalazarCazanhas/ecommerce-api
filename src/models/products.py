from datetime import datetime
from typing import List, Optional
from pydantic import UUID4
from sqlmodel import Field, Relationship, SQLModel

from src.models.base import BaseModel


# === Products Model ===
"""Product models DB"""
class ProductBase(SQLModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    image_url: Optional[str] = None

class Product(BaseModel, ProductBase, table=True):
    __tablename__ = "product"
    cart_items: List["CartItem"] = Relationship(back_populates="product") # type: ignore

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductRead(ProductBase):
    id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None