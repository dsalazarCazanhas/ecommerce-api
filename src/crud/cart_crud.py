from sqlmodel import Session, select
from typing import Optional

from src.models.cart import Cart, CartItem, CartStatus
from src.models.products import Product


def get_active_cart(session: Session, user_id: str) -> Cart:
    """
    Retrieve the user's active cart or create a new one if none exists.
    """
    cart = session.exec(
        select(Cart).where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
    ).first()

    if not cart:
        cart = Cart(user_id=user_id, status=CartStatus.ACTIVE)
        session.add(cart)
        session.commit()
        session.refresh(cart)

    return cart


def add_item_to_cart(session: Session, cart: Cart, product: Product, quantity: int) -> CartItem:
    """
    Add a product to the cart or update the quantity if it already exists.

    Args:
        session: Database session.
        cart: The user's active cart.
        product: The product to add.
        quantity: Quantity to add.

    Returns:
        The created or updated CartItem.
    """
    item = session.exec(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product.id
        )
    ).first()

    if item:
        item.quantity += quantity
    else:
        item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price
        )
        session.add(item)

    session.commit()
    session.refresh(item)
    return item


def remove_item(session: Session, item_id: str, user_id: str) -> Optional[bool]:
    """
    Remove a cart item if it belongs to the given user.

    Returns:
        None if not found, False if unauthorized, True if deleted.
    """
    item = session.get(CartItem, item_id)
    if not item:
        return None
    if item.cart.user_id != user_id:
        return False

    session.delete(item)
    session.commit()
    return True


def checkout_cart(session: Session, user_id: str) -> Optional[Cart]:
    """
    Mark the user's active cart as 'ORDERED'.

    Returns:
        The updated cart or None if no active/valid cart found.
    """
    cart = session.exec(
        select(Cart).where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
    ).first()

    if not cart or not cart.items:
        return None

    cart.status = CartStatus.ORDERED
    session.add(cart)
    session.commit()
    session.refresh(cart)
    return cart


def list_all_carts(session: Session) -> list[Cart]:
    """
    Retrieve all carts (admin only).
    """
    return session.exec(select(Cart)).all()
