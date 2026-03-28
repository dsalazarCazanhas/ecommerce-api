import datetime
import hashlib
import json
import math
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlmodel import select

from src.config.engine import SessionDep
from src.config.ext import settings
from src.crud import idempotency_crud
from src.models.auth import IdempotencyStatus
from src.models.order import Order, OrderItem, OrderStatus, Payment, PaymentStatus
from src.models.products import Product
from src.models.stripe import CheckoutRequest, PaymentMethodRequest, StripeWebhookEvent
from src.models.users import User
from src.security.auth import get_current_active_admin, get_current_user
from src.services.stripe_service import StripeService

stripe_router = APIRouter()

IDEMPOTENCY_SCOPE_STRIPE_CHECKOUT = "stripe_checkout"


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


def _stripe_checkout_request_hash(data: CheckoutRequest) -> str:
    """Stable hash for stripe checkout request payload."""
    payload = data.model_dump(mode="json")
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _validate_success_url(success_url: str) -> None:
    """Hosted checkout redirect should carry the session id placeholder."""
    if "{CHECKOUT_SESSION_ID}" not in success_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="success_url must include the {CHECKOUT_SESSION_ID} placeholder",
        )


def _build_checkout_line_items(db: SessionDep, order: Order) -> list[dict]:
    """Build Stripe line items from server-side order snapshots, not client input."""
    order_rows = db.exec(
        select(OrderItem, Product)
        .join(Product, Product.id == OrderItem.product_id)
        .where(OrderItem.order_id == order.id)
    ).all()

    if not order_rows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order has no payable items",
        )

    line_items: list[dict] = []
    computed_total = 0.0
    for order_item, product in order_rows:
        unit_amount = int(round(order_item.price_at_time * 100))
        if unit_amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order contains invalid payable amounts",
            )

        line_items.append(
            {
                "price_data": {
                    "currency": order.currency,
                    "product_data": {"name": product.name},
                    "unit_amount": unit_amount,
                },
                "quantity": order_item.quantity,
            }
        )
        computed_total += order_item.price_at_time * order_item.quantity

    if not math.isclose(computed_total, order.total_amount, abs_tol=0.01):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order total does not match its line items",
        )

    return line_items


def _resolve_order_from_event(db: SessionDep, payload: dict) -> Order | None:
    """Resolve the local order using the stored session id and Stripe metadata."""
    session_id = payload.get("id")
    if session_id:
        order = db.exec(
            select(Order).where(Order.stripe_session_id == session_id)
        ).first()
        if order:
            return order

    metadata = payload.get("metadata") or {}
    order_id = metadata.get("order_id") or payload.get("client_reference_id")
    if order_id:
        return db.get(Order, order_id)

    return None


def _get_existing_payment(
    db: SessionDep,
    *,
    order_id,
    session_id: str | None,
    payment_intent_id: str | None,
) -> Payment | None:
    """Resolve the payment record by intent, session, then order ownership."""
    if payment_intent_id:
        payment = db.exec(
            select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
        ).first()
        if payment:
            return payment

    if session_id:
        payment = db.exec(
            select(Payment).where(Payment.stripe_session_id == session_id)
        ).first()
        if payment:
            return payment

    return db.exec(select(Payment).where(Payment.order_id == order_id)).first()


def _apply_successful_checkout_event(db: SessionDep, payload: dict) -> None:
    """Mark order/payment as paid or processing from Checkout session events."""
    order = _resolve_order_from_event(db, payload)
    if not order:
        raise ValueError("Unable to resolve order for Stripe checkout event")

    session_id = payload.get("id")
    payment_intent_id = payload.get("payment_intent")
    amount_total = (payload.get("amount_total") or 0) / 100
    payment_status = payload.get("payment_status")

    payment = _get_existing_payment(
        db,
        order_id=order.id,
        session_id=session_id,
        payment_intent_id=payment_intent_id,
    )
    if not payment:
        payment = Payment(order_id=order.id)

    payment.stripe_session_id = session_id
    payment.stripe_payment_intent_id = payment_intent_id
    payment.amount = amount_total
    payment.currency = order.currency
    payment.updated_at = datetime.datetime.now(datetime.timezone.utc)

    order.stripe_session_id = session_id
    if payment_intent_id:
        order.stripe_payment_intent_id = payment_intent_id
    order.updated_at = datetime.datetime.now(datetime.timezone.utc)

    if payment_status in {"paid", "no_payment_required"}:
        order.status = OrderStatus.PAID
        payment.status = PaymentStatus.SUCCEEDED
    else:
        payment.status = PaymentStatus.PROCESSING

    db.add(order)
    db.add(payment)


def _apply_failed_payment_event(db: SessionDep, payload: dict) -> None:
    """Mark the local payment/order as failed when Stripe reports failure."""
    payment_intent_id = payload.get("id") or payload.get("payment_intent")
    order = _resolve_order_from_event(db, payload)
    payment = None
    if order:
        payment = _get_existing_payment(
            db,
            order_id=order.id,
            session_id=payload.get("id"),
            payment_intent_id=payment_intent_id,
        )
    elif payment_intent_id:
        payment = db.exec(
            select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
        ).first()
        if payment:
            order = db.get(Order, payment.order_id)

    if not order and not payment:
        raise ValueError("Unable to resolve payment for Stripe failure event")

    if payment:
        payment.status = PaymentStatus.FAILED
        payment.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.add(payment)

    if order and order.status != OrderStatus.PAID:
        order.status = OrderStatus.FAILED
        order.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.add(order)


def _apply_refund_event(db: SessionDep, payload: dict) -> None:
    """Mark the payment and order as refunded."""
    payment_intent_id = payload.get("payment_intent")
    if not payment_intent_id:
        raise ValueError("Refund event missing payment_intent id")

    payment = db.exec(
        select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
    ).first()
    if not payment:
        raise ValueError("Unable to resolve payment for Stripe refund event")

    order = db.get(Order, payment.order_id)
    payment.status = PaymentStatus.REFUNDED
    payment.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.add(payment)

    if order:
        order.status = OrderStatus.REFUNDED
        order.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.add(order)


# === ROUTES ===
@stripe_router.post("/checkout", summary="Create Stripe checkout session")
def create_checkout_session(
    data: CheckoutRequest,
    db: SessionDep,
    current_user: User = Depends(get_current_user),
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    normalized_key = _normalize_and_validate_idempotency_key(idempotency_key)
    request_hash = _stripe_checkout_request_hash(data)
    _validate_success_url(data.success_url)

    order = db.get(Order, data.order_id)
    if not order or str(order.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Order not found")

    record = idempotency_crud.get_by_user_and_key(
        db,
        user_id=order.user_id,
        idempotency_key=normalized_key,
        scope=IDEMPOTENCY_SCOPE_STRIPE_CHECKOUT,
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
                detail="Stripe checkout request with this Idempotency-Key is already in progress",
            )

        if record.response_body:
            cached_payload = json.loads(record.response_body)
            if record.response_status_code and record.response_status_code != 200:
                raise HTTPException(
                    status_code=record.response_status_code,
                    detail=cached_payload.get("detail", "Stripe checkout failed"),
                )
            return cached_payload

    record = idempotency_crud.create_processing(
        db,
        user_id=order.user_id,
        idempotency_key=normalized_key,
        request_hash=request_hash,
        scope=IDEMPOTENCY_SCOPE_STRIPE_CHECKOUT,
    )

    if record.request_hash != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with a different request",
        )

    if record.status == IdempotencyStatus.COMPLETED and record.response_body:
        return json.loads(record.response_body)

    if record.status == IdempotencyStatus.FAILED and record.response_body:
        cached_payload = json.loads(record.response_body)
        raise HTTPException(
            status_code=record.response_status_code or status.HTTP_409_CONFLICT,
            detail=cached_payload.get("detail", "Stripe checkout failed"),
        )

    try:
        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=409,
                detail="Order is not in a payable state",
            )
        if order.stripe_session_id:
            raise HTTPException(
                status_code=409,
                detail="Order already has an associated Stripe session",
            )

        items = _build_checkout_line_items(db, order)
        metadata = {
            "order_id": str(order.id),
            "user_id": str(order.user_id),
        }
        checkout_session = StripeService.create_checkout_session(
            line_items=items,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
            metadata=metadata,
            client_reference_id=str(order.id),
            idempotency_key=normalized_key,
        )

        order.stripe_session_id = checkout_session["id"]
        order.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db_payment_intent = checkout_session.get("payment_intent")
        if db_payment_intent:
            order.stripe_payment_intent_id = db_payment_intent
        db.add(order)
        db.commit()
        db.refresh(order)

        response_payload = {
            "session_url": checkout_session["url"],
            "session_id": checkout_session["id"],
            "order_id": str(order.id),
        }
        idempotency_crud.mark_completed(
            db,
            record=record,
            response_status_code=status.HTTP_200_OK,
            response_body=json.dumps(response_payload),
        )
        return response_payload
    except HTTPException as exc:
        idempotency_crud.mark_failed(
            db,
            record=record,
            response_status_code=exc.status_code,
            response_body=json.dumps({"detail": str(exc.detail)}),
        )
        raise exc
    except Exception as e:
        idempotency_crud.mark_failed(
            db,
            record=record,
            response_status_code=status.HTTP_400_BAD_REQUEST,
            response_body=json.dumps({"detail": str(e)}),
        )
        raise HTTPException(status_code=400, detail=str(e))


@stripe_router.get("/checkout/{session_id}", summary="Retrieve checkout session")
def get_checkout_session(session_id: str, _: User = Depends(get_current_active_admin)):
    try:
        return StripeService.retrieve_checkout_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@stripe_router.get("/checkout", summary="List recent checkout sessions")
def list_checkout_sessions(
    limit: int = 10, _: User = Depends(get_current_active_admin)
):
    try:
        return StripeService.list_all_checkout_sessions(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@stripe_router.post("/payment-method", summary="Create test payment method")
def create_payment_method(
    data: PaymentMethodRequest, _: User = Depends(get_current_active_admin)
):
    try:
        return StripeService.create_payment_method(
            account_number=data.account_number,
            routing_number=data.routing_number,
            holder_name=data.holder_name,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@stripe_router.get("/payment-methods/{customer_id}", summary="List customer payment methods")
def list_customer_payment_methods(
    customer_id: str,
    limit: int = 5,
    _: User = Depends(get_current_active_admin),
):
    try:
        return StripeService.list_customer_payment_methods(customer_id, limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@stripe_router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, session: SessionDep):
    """Stripe webhook handler for payment events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    event_id = event["id"]
    event_type = event["type"]
    data = event["data"]["object"]

    existing_event = session.exec(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event_id)
    ).first()
    if existing_event:
        return {"status": "already_processed"}

    try:
        if event_type in {
            "checkout.session.completed",
            "checkout.session.async_payment_succeeded",
        }:
            _apply_successful_checkout_event(session, data)
        elif event_type in {
            "checkout.session.async_payment_failed",
            "payment_intent.payment_failed",
        }:
            _apply_failed_payment_event(session, data)
        elif event_type == "charge.refunded":
            _apply_refund_event(session, data)

        session.add(
            StripeWebhookEvent(
                stripe_event_id=event_id,
                event_type=event_type,
            )
        )
        session.commit()
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Stripe webhook",
        ) from exc

    return {"status": "success"}
