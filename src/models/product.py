from typing import Optional
from sqlmodel import Relationship, SQLModel, Field
from datetime import datetime
from src.models.base import BaseModel


class Product(BaseModel, SQLModel, table=True):
    __tablename__ = "product"

    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    image_url: Optional[str] = None

class ProductCreate(Product):
    pass

class ProductRead(Product):
    pass

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
