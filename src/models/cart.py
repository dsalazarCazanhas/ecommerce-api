from typing import List
from pydantic import UUID4
from sqlmodel import Field, Relationship
from src.models.base import BaseModel
from src.models.product import Product

class Cart(BaseModel, table=True):
    __tablename__ = "cart"

    # cada usuario tiene al menos un carrito “activo” o en estado “abierto”
    user_id: UUID4 = Field(foreign_key="user.id")
    # opcional: estado del carrito (ej. “active”, “abandoned”, “ordered”)
    status: str = Field(default="active")
    
    # relación inversa
    items: List["CartItem"] = Relationship(back_populates="cart")

class CartItem(BaseModel, table=True):
    __tablename__ = "cart_item"

    cart_id: UUID4 = Field(foreign_key="cart.id")
    product_id: UUID4 = Field(foreign_key="product.id")
    quantity: int = Field(default=1, ge=1)
    
    # para snapshot en el carrito podrías almacenar precio en el momento
    unit_price: float = Field(..., description="Precio por unidad al momento de agregar; requerido para snapshot en el carrito")  # requerido
    
    cart: "Cart" = Relationship(back_populates="items")
    product: "Product" = Relationship(back_populates="cart_items")

