from datetime import datetime, timezone
from typing import Optional

from pydantic import UUID4
from sqlmodel import Session, select

from src.models.cart import Cart, CartItem, CartStatus
from src.models.order import Order, OrderItem, OrderStatus
from src.models.products import Product


def get_active_cart(session: Session, user_id: UUID4) -> Cart:
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


def add_item_to_cart(
    session: Session, cart: Cart, product: Product, quantity: int
) -> CartItem:
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
            CartItem.cart_id == cart.id, CartItem.product_id == product.id
        )
    ).first()

    if quantity < 1:
        raise ValueError("Quantity must be at least 1")

    if item:
        new_quantity = item.quantity + quantity
        if new_quantity > product.stock:
            raise ValueError("Requested quantity exceeds available stock")
        item.quantity = new_quantity
    else:
        if quantity > product.stock:
            raise ValueError("Requested quantity exceeds available stock")
        item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price,
        )
        session.add(item)

    session.commit()
    session.refresh(item)
    return item


def remove_item(session: Session, item_id: UUID4, user_id: UUID4) -> Optional[bool]:
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


def checkout_cart(session: Session, user_id: UUID4) -> Optional[tuple[Cart, Order]]:
    """
    Finalize checkout for the user's active cart.

    Domain flow:
        1. Validate active cart existence and that it has items.
        2. Revalidate inventory against current product stock.
        3. Create Order and OrderItem snapshots.
        4. Decrement product stock.
        5. Mark cart as ORDERED.

    The function commits once at the end so order creation, stock updates,
    and cart status transition happen atomically.

    Returns:
        Tuple of (updated cart, created order) or None if no active/valid cart found.
    """
    cart = session.exec(
        select(Cart).where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
    ).first()

    if not cart or not cart.items:
        return None

    checkout_lines: list[tuple[CartItem, Product]] = []
    total_amount = 0.0

    for item in cart.items:
        product = session.get(Product, item.product_id)
        if not product:
            raise ValueError("One or more products in cart are no longer available")
        if item.quantity > product.stock:
            raise ValueError("Insufficient stock for one or more cart items")

        checkout_lines.append((item, product))
        total_amount += item.unit_price * item.quantity

    order = Order(user_id=user_id, total_amount=total_amount)
    session.add(order)
    session.flush()

    for item, product in checkout_lines:
        product.stock -= item.quantity
        session.add(product)

        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_time=item.unit_price,
        )
        session.add(order_item)

    cart.status = CartStatus.ORDERED
    cart.updated_at = datetime.now(timezone.utc)
    session.add(cart)
    session.commit()
    session.refresh(cart)
    session.refresh(order)
    order.status = OrderStatus.PENDING
    return cart, order


def list_all_carts(session: Session) -> list[Cart]:
    """
    Retrieve all carts (admin only).
    """
    return session.exec(select(Cart)).all()
