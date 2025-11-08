import datetime

import stripe
from fastapi import APIRouter, HTTPException, Request, status
from sqlmodel import Session, select

from src.config.engine import get_session
from src.config.ext import settings
from src.models.order import Order, Payment
from src.models.stripe import CheckoutRequest, PaymentMethodRequest
from src.services.stripe_service import StripeService

router = APIRouter()


# === ROUTES ===
@router.post("/checkout", summary="Create Stripe checkout session")
def create_checkout_session(data: CheckoutRequest):
    try:
        items = [
            {
                "price_data": {
                    "currency": i.currency,
                    "product_data": {"name": i.name},
                    "unit_amount": i.amount,
                },
                "quantity": i.quantity,
            }
            for i in data.line_items
        ]
        session = StripeService.create_checkout_session(
            line_items=items,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
        return {"session_url": session["url"], "session_id": session["id"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/checkout/{session_id}", summary="Retrieve checkout session")
def get_checkout_session(session_id: str):
    try:
        return StripeService.retrieve_checkout_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/checkout", summary="List recent checkout sessions")
def list_checkout_sessions(limit: int = 10):
    try:
        return StripeService.list_all_checkout_sessions(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payment-method", summary="Create test payment method")
def create_payment_method(data: PaymentMethodRequest):
    try:
        return StripeService.create_payment_method(
            account_number=data.account_number,
            routing_number=data.routing_number,
            holder_name=data.holder_name,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payment-methods/{customer_id}", summary="List customer payment methods")
def list_customer_payment_methods(customer_id: str, limit: int = 5):
    try:
        return StripeService.list_customer_payment_methods(customer_id, limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, session: Session = get_session()):
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

    event_type = event["type"]
    data = event["data"]["object"]

    print(f"🔔 Received Stripe event: {event_type}")

    # === Handle checkout completion ===
    if event_type == "checkout.session.completed":
        session_id = data.get("id")
        payment_intent_id = data.get("payment_intent")
        amount_total = data.get("amount_total", 0) / 100  # Stripe sends cents

        # Buscar orden asociada
        db_order = session.exec(
            select(Order).where(Order.stripe_session_id == session_id)
        ).first()

        if db_order:
            db_order.status = "paid"
            db_order.updated_at = datetime.now(datetime.timezone.utc)

            # Crear registro de pago
            payment = Payment(
                order_id=db_order.id,
                stripe_session_id=session_id,
                stripe_payment_intent_id=payment_intent_id,
                amount=amount_total,
                status="succeeded",
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)

            print(f"✅ Order {db_order.id} marked as PAID")

    # === Handle payment failure ===
    elif event_type == "payment_intent.payment_failed":
        payment_intent_id = data.get("id")
        db_payment = session.exec(
            select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
        ).first()
        if db_payment:
            db_payment.status = "failed"
            db_payment.updated_at = datetime.now(datetime.timezone.utc)
            db_order = session.get(Order, db_payment.order_id)
            if db_order:
                db_order.status = "failed"
                db_order.updated_at = datetime.now(datetime.timezone.utc)
            session.commit()
            print(f"❌ Payment {db_payment.id} failed")

    # === Handle refunds ===
    elif event_type == "charge.refunded":
        payment_intent_id = data.get("payment_intent")
        db_payment = session.exec(
            select(Payment).where(Payment.stripe_payment_intent_id == payment_intent_id)
        ).first()
        if db_payment:
            db_payment.status = "refunded"
            db_payment.updated_at = datetime.now(datetime.timezone.utc)
            db_order = session.get(Order, db_payment.order_id)
            if db_order:
                db_order.status = "refunded"
                db_order.updated_at = datetime.now(datetime.timezone.utc)
            session.commit()
            print(f"💸 Payment {db_payment.id} refunded")

    else:
        print(f"ℹ️ Event {event_type} ignored")

    return {"status": "success"}
    return {"status": "success"}
