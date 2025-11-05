from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from src.config.engine import get_session
from src.models.users import User, UserRead
from src.models.products import Product
from src.security.auth import get_current_user, get_current_active_admin
from src.models.cart import Cart, CartItem
from src.crud import cart_crud


router = APIRouter()

@router.get("/", response_model=Cart)
def get_cart(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the current user's active cart.
    If no cart exists, a new one is created.
    """
    return cart_crud.get_active_cart(session, current_user.id)


@router.post("/add", response_model=Cart)
def add_to_cart(
    product_id: str,
    quantity: int = 1,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Add a product to the user's active cart or update its quantity.
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart = cart_crud.get_active_cart(session, current_user.id)
    cart_crud.add_item_to_cart(session, cart, product, quantity)
    return cart


@router.delete("/item/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    item_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a cart item belonging to the current user.
    """
    result = cart_crud.remove_item(session, item_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if result is False:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("/checkout", response_model=Cart)
def checkout_cart(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Complete the checkout process by marking the active cart as 'ORDERED'.
    """
    cart = cart_crud.checkout_cart(session, current_user.id)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty or not found")
    return cart


@router.get("/admin/all", response_model=list[Cart])
def list_carts(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_active_admin)
):
    """
    List all carts (admin only).
    """
    return cart_crud.list_all_carts(session)



@router.get("/me/items")
def list_cart_items(current_user: UserRead = Depends(get_current_user), session: Session = Depends(get_session)):
    # Get active cart for user
    cart = session.exec(
        select(Cart).where(Cart.user_id == current_user.id, Cart.status == "active")
    ).first()

    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Get cart items with product info
    items = session.exec(
        select(CartItem)
        .where(CartItem.cart_id == cart.id)
        .join(Product)
    ).all()

    # Optional: return as clean JSON
    result = [
        {
            "product_id": item.product.id,
            "name": item.product.name,
            "price": item.unit_price,
            "quantity": item.quantity,
            "subtotal": item.quantity * item.unit_price
        }
        for item in items
    ]

    return {"cart_id": cart.id, "items": result}