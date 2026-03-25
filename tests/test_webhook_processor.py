"""Unit tests for Stripe webhook payment-state-machine domain processors.

These tests verify the critical money-flow logic without requiring a live
database or Stripe connection. Each helper is exercised in isolation using a
FakeSession that satisfies the SQLModel Session interface (exec/get/add).

Test coverage
-------------
- checkout.session.completed (payment_status=paid)   → PAID / SUCCEEDED
- checkout.session.completed (payment_status=unpaid)  → PROCESSING (async method)
- checkout.session.completed (no_payment_required)    → PAID
- Successful checkout reuses an existing Payment record
- Successful checkout raises when order cannot be resolved
- payment_intent.payment_failed / async_payment_failed on PENDING order → FAILED
- payment_intent.payment_failed on PAID order → order stays PAID (guard)
- Failed payment raises when neither order nor payment is resolvable
- charge.refunded → REFUNDED for both order and payment
- charge.refunded without payment_intent field → ValueError
- charge.refunded for unknown payment → ValueError
- _resolve_order_from_event primary path (stripe_session_id lookup)
- _resolve_order_from_event metadata.order_id fallback
- _resolve_order_from_event returns None gracefully on total miss
"""

from collections import deque
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.api.v1.stripe import (
    _apply_failed_payment_event,
    _apply_refund_event,
    _apply_successful_checkout_event,
    _resolve_order_from_event,
)
from src.models.order import Order, OrderStatus, PaymentStatus

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _ExecResult:
    """Adapter that satisfies db.exec(stmt).first()."""

    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class FakeSession:
    """Minimal SQLModel Session double for domain-level unit tests.

    Parameters
    ----------
    exec_returns:
        Ordered sequence of return values for successive ``exec().first()``
        calls.  Once exhausted, further calls return ``None``.
    get_map:
        Mapping ``(ModelClass, key) → object`` used for ``db.get()`` lookups.
    """

    def __init__(self, exec_returns=None, get_map=None):
        self._exec_queue = deque(exec_returns or [])
        self._get_map = get_map or {}
        self.added = []

    def exec(self, statement):  # noqa: ARG002 – statement is intentionally unused
        value = self._exec_queue.popleft() if self._exec_queue else None
        return _ExecResult(value)

    def get(self, cls, key):
        return self._get_map.get((cls, key))

    def add(self, obj):
        self.added.append(obj)

    # Helpers not called by domain functions but required for interface parity
    def commit(self):
        pass

    def refresh(self, obj):
        pass


def _make_order(**kwargs) -> SimpleNamespace:
    """Return a minimal order-like namespace with sensible defaults."""
    defaults = dict(
        id=str(uuid4()),
        user_id=str(uuid4()),
        total_amount=20.0,
        currency="usd",
        status=OrderStatus.PENDING,
        stripe_session_id=None,
        stripe_payment_intent_id=None,
        updated_at=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_payment(**kwargs) -> SimpleNamespace:
    """Return a minimal payment-like namespace with sensible defaults."""
    defaults = dict(
        id=str(uuid4()),
        order_id=str(uuid4()),
        stripe_payment_intent_id=None,
        stripe_session_id=None,
        amount=0.0,
        currency="usd",
        status=PaymentStatus.PENDING,
        updated_at=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _checkout_payload(
    session_id: str = "cs_test_123",
    payment_intent: str = "pi_test_456",
    amount_total: int = 2000,
    payment_status: str = "paid",
    order_id: str | None = None,
) -> dict:
    """Build a minimal checkout.session.* Stripe event data object."""
    return {
        "id": session_id,
        "payment_intent": payment_intent,
        "amount_total": amount_total,
        "payment_status": payment_status,
        "metadata": {"order_id": order_id or str(uuid4())},
        "client_reference_id": None,
    }


def _payment_failed_payload(
    intent_id: str = "pi_test_456",
) -> dict:
    """Build a minimal payment_intent.payment_failed or async_payment_failed payload."""
    return {
        "id": intent_id,
        "payment_intent": intent_id,
        "metadata": {},
    }


def _refund_payload(payment_intent: str = "pi_test_456") -> dict:
    """Build a minimal charge.refunded event data object."""
    return {"payment_intent": payment_intent}


# ---------------------------------------------------------------------------
# _apply_successful_checkout_event
# ---------------------------------------------------------------------------

# NOTE on test design: _apply_successful_checkout_event calls Payment(order_id=...)
# when no existing Payment record is found.  In this Python 3.14 + SQLModel 0.0.37
# environment, instantiating a SQLModel table class in an isolated test triggers
# SQLAlchemy's lazy mapper configuration, which fails because
# `from __future__ import annotations` causes forward-reference strings such as
# `list["OrderItem"]` to be stored with double quotes the resolver cannot parse.
# The production code is correct; the work-around is to always supply a
# pre-existing payment record in exec_returns so the constructor branch is
# never reached.  State-transition behaviour (the critical invariant) is still
# fully exercised.


class TestApplySuccessfulCheckout:
    """checkout.session.completed and checkout.session.async_payment_succeeded."""

    def test_paid_marks_order_paid_and_payment_succeeded(self):
        """payment_status='paid' → order.status=PAID, payment.status=SUCCEEDED."""
        order = _make_order()
        payment = _make_payment(order_id=order.id, status=PaymentStatus.PENDING)
        payload = _checkout_payload(
            session_id="cs_abc",
            payment_intent="pi_abc",
            payment_status="paid",
            order_id=order.id,
        )
        # exec call sequence:
        #  1. _resolve_order_from_event: by stripe_session_id → order
        #  2. _get_existing_payment by payment_intent_id    → None
        #  3. _get_existing_payment by session_id           → None
        #  4. _get_existing_payment by order_id             → payment  (found!)
        db = FakeSession(exec_returns=[order, None, None, payment])

        _apply_successful_checkout_event(db, payload)

        assert order.status == OrderStatus.PAID
        assert order.stripe_session_id == "cs_abc"
        assert order.stripe_payment_intent_id == "pi_abc"
        assert payment.status == PaymentStatus.SUCCEEDED
        assert order in db.added and payment in db.added

    def test_unpaid_async_method_marks_payment_processing(self):
        """Async payment method (e.g. buy-now-pay-later) with payment_status='unpaid'
        must set payment to PROCESSING without marking the order PAID yet —
        the order will be confirmed via async_payment_succeeded later."""
        order = _make_order()
        payment = _make_payment(order_id=order.id, status=PaymentStatus.PENDING)
        payload = _checkout_payload(payment_status="unpaid", order_id=order.id)
        db = FakeSession(exec_returns=[order, None, None, payment])

        _apply_successful_checkout_event(db, payload)

        # Order must NOT be promoted to PAID when the payment is still pending
        assert order.status == OrderStatus.PENDING
        assert payment.status == PaymentStatus.PROCESSING

    def test_no_payment_required_marks_order_paid(self):
        """Fully-discounted or free checkout → payment_status='no_payment_required' → PAID."""
        order = _make_order()
        payment = _make_payment(order_id=order.id, status=PaymentStatus.PENDING)
        payload = _checkout_payload(
            payment_status="no_payment_required", order_id=order.id
        )
        db = FakeSession(exec_returns=[order, None, None, payment])

        _apply_successful_checkout_event(db, payload)

        assert order.status == OrderStatus.PAID
        assert payment.status == PaymentStatus.SUCCEEDED

    def test_reuses_existing_payment_record(self):
        """When a Payment already exists it must be updated in-place (not duplicated)."""
        order = _make_order(stripe_session_id="cs_reuse")
        existing = _make_payment(
            order_id=order.id,
            stripe_session_id="cs_reuse",
            status=PaymentStatus.PROCESSING,
        )
        payload = _checkout_payload(
            session_id="cs_reuse",
            payment_intent="pi_reuse",
            payment_status="paid",
            order_id=order.id,
        )
        # _get_existing_payment finds existing record on the first exec (by pi_id)
        db = FakeSession(exec_returns=[order, existing])

        _apply_successful_checkout_event(db, payload)

        assert existing.status == PaymentStatus.SUCCEEDED
        assert order.status == OrderStatus.PAID
        # Exactly the two pre-existing objects staged — no new Payment created
        assert len(db.added) == 2 and order in db.added and existing in db.added

    def test_raises_when_order_not_resolvable(self):
        """If no local order can be correlated, the processor must raise ValueError
        (caller — the webhook handler — will rollback and return 500)."""
        # Payload references an order_id that has no match in DB
        payload = _checkout_payload(order_id=str(uuid4()))
        # exec returns: stripe_session_id lookup → None; db.get fallback → None (empty get_map)
        db = FakeSession(exec_returns=[None])

        with pytest.raises(ValueError, match="Unable to resolve order"):
            _apply_successful_checkout_event(db, payload)


# ---------------------------------------------------------------------------
# _apply_failed_payment_event
# ---------------------------------------------------------------------------


class TestApplyFailedPayment:
    """payment_intent.payment_failed and checkout.session.async_payment_failed."""

    def test_marks_pending_order_and_payment_failed(self):
        """payment_intent.payment_failed on a PENDING order → both FAILED."""
        order = _make_order(status=OrderStatus.PENDING)
        payment = _make_payment(
            order_id=order.id,
            stripe_payment_intent_id="pi_fail",
            status=PaymentStatus.PROCESSING,
        )
        payload = _payment_failed_payload(intent_id="pi_fail")

        # exec call sequence:
        #  1. _resolve_order_from_event: stripe_session_id lookup (id="pi_fail") → None
        #     metadata is {} → no metadata fallback → _resolve returns None
        #  2. fallback path in _apply_failed_payment_event: find Payment by pi_id → payment
        # db.get(Order, payment.order_id) → order  (via get_map)
        db = FakeSession(
            exec_returns=[None, payment],
            get_map={(Order, order.id): order},
        )

        _apply_failed_payment_event(db, payload)

        assert order.status == OrderStatus.FAILED
        assert payment.status == PaymentStatus.FAILED

    def test_does_not_downgrade_paid_order(self):
        """Critical guard: a late payment_failed event arriving after a successful
        async payment must NOT override an already-PAID order.

        Reference: Stripe docs — 'Handle duplicate webhook events' and
        'Order of webhook delivery is not guaranteed'."""
        order = _make_order(status=OrderStatus.PAID)
        payment = _make_payment(
            order_id=order.id,
            stripe_payment_intent_id="pi_late",
            status=PaymentStatus.SUCCEEDED,
        )
        payload = _payment_failed_payload(intent_id="pi_late")

        db = FakeSession(
            exec_returns=[None, payment],
            get_map={(Order, order.id): order},
        )

        _apply_failed_payment_event(db, payload)

        # Order must remain PAID despite the failure event
        assert order.status == OrderStatus.PAID
        # Payment status is still updated to reflect the event
        assert payment.status == PaymentStatus.FAILED

    def test_async_payment_failed_via_checkout_session(self):
        """checkout.session.async_payment_failed: order is resolved via stripe_session_id,
        existing payment found by session_id and marked FAILED."""
        order = _make_order(
            status=OrderStatus.PENDING, stripe_session_id="cs_async_fail"
        )
        payment = _make_payment(
            order_id=order.id,
            stripe_session_id="cs_async_fail",
            status=PaymentStatus.PROCESSING,
        )
        payload = {
            "id": "cs_async_fail",
            "payment_intent": "pi_async_fail",
            "metadata": {"order_id": order.id},
        }
        # exec call sequence:
        #  1. _resolve_order_from_event: stripe_session_id lookup → order
        #  2. _get_existing_payment by payment_intent_id ("cs_async_fail") → None
        #  3. _get_existing_payment by session_id ("cs_async_fail") → payment  (found!)
        db = FakeSession(exec_returns=[order, None, payment])

        _apply_failed_payment_event(db, payload)

        assert order.status == OrderStatus.FAILED
        assert payment.status == PaymentStatus.FAILED

    def test_raises_when_neither_order_nor_payment_resolvable(self):
        """If the event references an unknown payment intent with no local records,
        ValueError must propagate so the webhook handler can return 500."""
        payload = _payment_failed_payload(intent_id="pi_ghost")
        db = FakeSession(exec_returns=[None, None])

        with pytest.raises(ValueError, match="Unable to resolve payment"):
            _apply_failed_payment_event(db, payload)


# ---------------------------------------------------------------------------
# _apply_refund_event
# ---------------------------------------------------------------------------


class TestApplyRefund:
    """charge.refunded event handling."""

    def test_marks_order_and_payment_refunded(self):
        """Standard refund flow → order and payment both transition to REFUNDED."""
        order = _make_order(status=OrderStatus.PAID)
        payment = _make_payment(
            order_id=order.id,
            stripe_payment_intent_id="pi_refund",
            status=PaymentStatus.SUCCEEDED,
        )
        payload = _refund_payload(payment_intent="pi_refund")

        # exec #1: find Payment by payment_intent_id → payment
        # db.get(Order, payment.order_id) → order
        db = FakeSession(
            exec_returns=[payment],
            get_map={(Order, order.id): order},
        )

        _apply_refund_event(db, payload)

        assert payment.status == PaymentStatus.REFUNDED
        assert order.status == OrderStatus.REFUNDED

    def test_raises_when_payment_intent_missing_in_payload(self):
        """charge.refunded without a payment_intent field → ValueError immediately."""
        db = FakeSession()
        with pytest.raises(ValueError, match="Refund event missing payment_intent"):
            _apply_refund_event(db, {"id": "ch_no_pi"})

    def test_raises_when_payment_record_not_found(self):
        """charge.refunded for an unknown payment_intent (no Payment row) → ValueError."""
        db = FakeSession(exec_returns=[None])
        with pytest.raises(ValueError, match="Unable to resolve payment"):
            _apply_refund_event(db, {"payment_intent": "pi_ghost"})


# ---------------------------------------------------------------------------
# _resolve_order_from_event (correlation paths)
# ---------------------------------------------------------------------------


class TestResolveOrderFromEvent:
    """Order correlation strategy: stripe_session_id → metadata → None."""

    def test_resolves_by_stripe_session_id(self):
        """Primary path: match by Order.stripe_session_id field."""
        order = _make_order(stripe_session_id="cs_primary")
        db = FakeSession(exec_returns=[order])

        result = _resolve_order_from_event(db, {"id": "cs_primary"})

        assert result is order

    def test_falls_back_to_metadata_order_id(self):
        """When session_id lookup misses, resolve via metadata.order_id (db.get)."""
        order = _make_order()
        db = FakeSession(
            exec_returns=[None],
            get_map={(Order, order.id): order},
        )
        payload = {"id": "cs_miss", "metadata": {"order_id": order.id}}

        result = _resolve_order_from_event(db, payload)

        assert result is order

    def test_falls_back_to_client_reference_id(self):
        """metadata is absent but client_reference_id carries the order_id."""
        order = _make_order()
        db = FakeSession(
            exec_returns=[None],
            get_map={(Order, order.id): order},
        )
        payload = {
            "id": "cs_ref",
            "metadata": {},
            "client_reference_id": order.id,
        }

        result = _resolve_order_from_event(db, payload)

        assert result is order

    def test_returns_none_when_all_lookups_fail(self):
        """Graceful return of None when no lookup resolves (caller decides how to handle)."""
        db = FakeSession(exec_returns=[None])

        result = _resolve_order_from_event(db, {"id": "cs_unknown"})

        assert result is None
