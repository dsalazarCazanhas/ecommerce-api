import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import UUID4
from sqlmodel import select

from src.config.engine import SessionDep
from src.crud import cart_crud, idempotency_crud
from src.models.auth import IdempotencyStatus
from src.models.cart import Cart, CartItem, CartStatus
from src.models.order import CheckoutSummary
from src.models.products import Product
from src.models.users import User, UserRead
from src.security.auth import get_current_active_admin, get_current_user

cart_router = APIRouter()

IDEMPOTENCY_SCOPE_CHECKOUT = "cart_checkout"


def _normalize_and_validate_idempotency_key(raw_key: str) -> str:
    """Validate and normalize idempotency key to canonical UUIDv4 string."""
    normalized = raw_key.strip()
    if len(normalized) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must be 64 characters or less",
        )

    try:
        parsed = UUID(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must be a valid UUIDv4",
        ) from exc

    if parsed.version != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must be a valid UUIDv4",
        )

    return str(parsed)


def _checkout_request_hash() -> str:
    """Stable hash for checkout request payload (currently empty body endpoint)."""
    return hashlib.sha256(b"{}").hexdigest()


@cart_router.get("/", response_model=Cart, status_code=status.HTTP_200_OK)
def get_cart(session: SessionDep, current_user: User = Depends(get_current_user)):
    """
    Retrieve the current user's active cart.
    If no cart exists, a new one is created.
    """
    return cart_crud.get_active_cart(session, current_user.id)


@cart_router.post("/add", response_model=Cart, status_code=status.HTTP_200_OK)
def add_to_cart(
    product_id: UUID4,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    quantity: int = 1,
):
    """
    Add a product to the user's active cart or update its quantity.
    """
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart = cart_crud.get_active_cart(session, current_user.id)
    try:
        cart_crud.add_item_to_cart(session, cart, product, quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return cart


@cart_router.delete("/item/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(
    item_id: UUID4, session: SessionDep, current_user: User = Depends(get_current_user)
):
    """
    Delete a cart item belonging to the current user.
    """
    result = cart_crud.remove_item(session, item_id, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if result is False:
        raise HTTPException(status_code=403, detail="Not authorized")


@cart_router.post(
    "/checkout", response_model=CheckoutSummary, status_code=status.HTTP_200_OK
)
def checkout_cart(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    """
    Complete checkout with server-side idempotency guarantees.
    """
    normalized_key = _normalize_and_validate_idempotency_key(idempotency_key)
    request_hash = _checkout_request_hash()

    record = idempotency_crud.get_by_user_and_key(
        session,
        user_id=current_user.id,
        idempotency_key=normalized_key,
        scope=IDEMPOTENCY_SCOPE_CHECKOUT,
    )

    if record:
        if record.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency-Key was already used with a different request",
            )

        if record.status == IdempotencyStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Checkout request with this Idempotency-Key is already in progress",
            )

        if record.response_body:
            cached_payload = json.loads(record.response_body)
            if record.response_status_code and record.response_status_code != 200:
                raise HTTPException(
                    status_code=record.response_status_code,
                    detail=cached_payload.get("detail", "Checkout failed"),
                )
            return CheckoutSummary(**cached_payload)

    record = idempotency_crud.create_processing(
        session,
        user_id=current_user.id,
        idempotency_key=normalized_key,
        request_hash=request_hash,
        scope=IDEMPOTENCY_SCOPE_CHECKOUT,
    )

    if record.request_hash != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with a different request",
        )
    if record.status == IdempotencyStatus.COMPLETED and record.response_body:
        return CheckoutSummary(**json.loads(record.response_body))
    if record.status == IdempotencyStatus.FAILED and record.response_body:
        cached_payload = json.loads(record.response_body)
        raise HTTPException(
            status_code=record.response_status_code or status.HTTP_409_CONFLICT,
            detail=cached_payload.get("detail", "Checkout failed"),
        )

    try:
        checkout_result = cart_crud.checkout_cart(session, current_user.id)
    except ValueError as exc:
        error_payload = {"detail": str(exc)}
        idempotency_crud.mark_failed(
            session,
            record=record,
            response_status_code=status.HTTP_409_CONFLICT,
            response_body=json.dumps(error_payload),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    if not checkout_result:
        error_payload = {"detail": "Cart is empty or not found"}
        idempotency_crud.mark_failed(
            session,
            record=record,
            response_status_code=status.HTTP_400_BAD_REQUEST,
            response_body=json.dumps(error_payload),
        )
        raise HTTPException(status_code=400, detail="Cart is empty or not found")

    cart, order = checkout_result
    summary = CheckoutSummary(
        order_id=order.id,
        cart_id=cart.id,
        order_status=order.status,
        total_amount=order.total_amount,
        currency=order.currency,
    )

    idempotency_crud.mark_completed(
        session,
        record=record,
        response_status_code=status.HTTP_200_OK,
        response_body=json.dumps(summary.model_dump(mode="json")),
    )

    return summary


@cart_router.get("/admin/all", response_model=list[Cart], status_code=status.HTTP_200_OK)
def list_carts(session: SessionDep, _: User = Depends(get_current_active_admin)):
    """
    List all carts (admin only).
    """
    return cart_crud.list_all_carts(session)


@cart_router.get("/me/items", status_code=status.HTTP_200_OK)
def list_cart_items(
    session: SessionDep, current_user: UserRead = Depends(get_current_user)
):
    # Get active cart for user
    cart = session.exec(
        select(Cart).where(
            Cart.user_id == current_user.id,
            Cart.status == CartStatus.ACTIVE,
        )
    ).first()

    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    # Get cart items with product info
    items = session.exec(
        select(CartItem).where(CartItem.cart_id == cart.id).join(Product)
    ).all()

    # Optional: return as clean JSON
    result = [
        {
            "product_id": item.product.id,
            "name": item.product.name,
            "price": item.unit_price,
            "quantity": item.quantity,
            "subtotal": item.quantity * item.unit_price,
        }
        for item in items
    ]

    return {"cart_id": cart.id, "items": result}
