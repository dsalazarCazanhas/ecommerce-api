from sqlmodel import select, Session
from src.models.product import Product, ProductCreate, ProductUpdate

def create_product(session: Session, product_data: ProductCreate) -> Product:
    product = Product.model_validate(product_data)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

def get_products(session: Session) -> list[Product]:
    return session.exec(select(Product)).all()

def get_product(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)

def update_product(session: Session, product_id: int, product_data: ProductUpdate) -> Product | None:
    product = session.get(Product, product_id)
    if not product:
        return None
    for key, value in product_data.dict(exclude_unset=True).items():
        setattr(product, key, value)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

def delete_product(session: Session, product_id: int) -> bool:
    product = session.get(Product, product_id)
    if not product:
        return False
    session.delete(product)
    session.commit()
    return True
