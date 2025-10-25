from datetime import datetime, timezone
from fastapi import HTTPException, status, APIRouter, Depends
from pydantic import UUID4
from sqlmodel import Session, select

from src.config.engine import get_session
from src.models.products import Product, ProductBase, ProductRead, ProductUpdate
from src.crud import products_crud
from src.models.users import User
from src.security.auth import get_current_active_admin


router = APIRouter()

@router.get("/", summary="Get all products")
def get_all_products(session: Session = Depends(get_session)):
    """Obtener todos los productos"""
    products = products_crud.get_products(session=session)
    if not products:
        raise HTTPException(status_code=404, detail="No products found.")
    return products

@router.get("/{product_id}", response_model=Product, summary="Get product by ID")
def get_product_by_id(product_id: UUID4, session: Session = Depends(get_session)) -> Product:
    """Obtener producto por ID"""
    product = products_crud.get_product_by_id(session=session, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product

@router.post("/register", response_model=ProductRead, summary="Register new product")
def register_new_product(product_data: ProductBase, session: Session = Depends(get_session), _: User = Depends(get_current_active_admin)):
    """Registrar nuevo producto con validaciones"""
    if products_crud.get_product_by_name(session=session, name=product_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product already registered"
        )

    return products_crud.create_product(product_data=product_data, session=session)

@router.patch("/{product_id}", response_model=ProductRead, summary="Update product")
def update_product(
    product_id: UUID4, product_update: ProductUpdate, session: Session = Depends(get_session), _: User = Depends(get_current_active_admin)
) -> Product:
    """Actualizar datos del producto"""
    product: Product = products_crud.get_product_by_id(session=session, product_id=product_id)
    for field, value in product_update.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    product.updated_at = datetime.now(timezone.utc)
    return products_crud.update_product(product=product, session=session)

@router.delete("/{product_id}", summary="Delete product")
def delete_product(product_id: UUID4, session: Session = Depends(get_session), _: User = Depends(get_current_active_admin)):
    """Eliminar producto por ID"""
    return products_crud.delete_product(product_id, session)