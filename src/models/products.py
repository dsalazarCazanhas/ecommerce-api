# src/models/products.py
from datetime import datetime
from typing import List, Optional
from pydantic import UUID4
from sqlmodel import Field, Relationship, SQLModel

from src.models.base import BaseModel


# === Products Model ===
"""Product models DB"""
class ProductBase(SQLModel, table = False):
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    image_url: Optional[str] = None

class Product(BaseModel, ProductBase, table=True):
    __tablename__ = "product"
    cart_items: List["CartItem"] = Relationship(back_populates="product") # type: ignore

class ProductUpdate(SQLModel, table = False):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None

class ProductCreate(ProductBase, table = False):
    pass

class ProductRead(ProductBase, table = False):
    id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None