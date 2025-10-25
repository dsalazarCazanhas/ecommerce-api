from pydantic import UUID4
from sqlmodel import select, Session
from src.models.products import Product, ProductBase

def create_product(session: Session, product_data: ProductBase) -> Product:
    product = Product(**product_data.model_dump())
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

def get_products(session: Session) -> list[Product]:
    return session.exec(select(Product)).all()

def get_product_by_id(session: Session, product_id: UUID4) -> Product | None:
    return session.get(Product, product_id)

def get_product_by_name(session: Session, name: str) -> Product | None:
    return session.exec(select(Product).where(Product.name == name)).first()

def update_product(session: Session, product: Product) -> Product | None:
    session.add(product)
    session.commit()
    session.refresh(product)
    return product

def delete_product(session: Session, product_id: UUID4) -> bool:
    product = get_product_by_id(session, product_id)
    if not product:
        return False
    session.delete(product)
    session.commit()
    return True
