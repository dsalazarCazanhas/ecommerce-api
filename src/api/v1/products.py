from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import UUID4

from src.config.engine import SessionDep
from src.crud import products_crud
from src.models.products import Product, ProductBase, ProductRead, ProductUpdate
from src.models.users import User
from src.security.auth import get_current_active_admin

router = APIRouter()


@router.get("/", summary="Get all products", status_code=status.HTTP_200_OK)
def get_all_products(session: SessionDep):
    """Get all products"""
    return products_crud.get_products(session=session)


@router.get(
    "/{product_id}",
    response_model=Product,
    summary="Get product by ID",
    status_code=status.HTTP_200_OK,
)
def get_product_by_id(product_id: UUID4, session: SessionDep) -> Product:
    """Get product by ID"""
    product = products_crud.get_product_by_id(session=session, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.post(
    "/register",
    response_model=ProductRead,
    summary="Register new product",
    status_code=status.HTTP_201_CREATED,
)
def register_new_product(
    product_data: ProductBase,
    session: SessionDep,
    _: User = Depends(get_current_active_admin),
):
    """Register a new product"""
    if products_crud.get_product_by_name(session=session, name=product_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Product already registered"
        )

    return products_crud.create_product(product_data=product_data, session=session)


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    summary="Update product by ID",
    status_code=status.HTTP_200_OK,
)
def update_product(
    product_id: UUID4,
    product_update: ProductUpdate,
    session: SessionDep,
    _: User = Depends(get_current_active_admin),
) -> Product:
    """Update product by ID"""
    product: Product = products_crud.get_product_by_id(
        session=session, product_id=product_id
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        )

    if product_update.name and product_update.name != product.name:
        existing_product = products_crud.get_product_by_name(
            session=session, name=product_update.name
        )
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product already registered",
            )

    for field, value in product_update.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    product.updated_at = datetime.now(timezone.utc)
    return products_crud.update_product(product=product, session=session)


@router.delete(
    "/{product_id}",
    summary="Delete product by ID",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product(
    product_id: UUID4, session: SessionDep, _: User = Depends(get_current_active_admin)
):
    """Delete product by ID"""
    success = products_crud.delete_product(session=session, product_id=product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found."
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
