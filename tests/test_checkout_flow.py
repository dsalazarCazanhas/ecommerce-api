"""Unit tests for checkout domain invariants using fakes.

These tests avoid global ORM mapper initialization and focus on checkout logic.
"""

from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from src.crud import cart_crud
from src.models.cart import CartStatus


@dataclass
class FakeProduct:
    id: str
    stock: int


@dataclass
class FakeCartItem:
    product_id: str
    quantity: int
    unit_price: float


@dataclass
class FakeCart:
    id: str
    user_id: str
    status: str
    items: list[FakeCartItem] = field(default_factory=list)
    updated_at: object | None = None


class FakeOrder:
    def __init__(self, user_id, total_amount):
        self.id = str(uuid4())
        self.user_id = user_id
        self.total_amount = total_amount
        self.currency = "usd"
        self.status = "pending"


class FakeOrderItem:
    def __init__(self, order_id, product_id, quantity, price_at_time):
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = quantity
        self.price_at_time = price_at_time


class FakeExecResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


class FakeSelect:
    def where(self, *args, **kwargs):
        return self


class FakeSession:
    def __init__(self, cart, products):
        self.cart = cart
        self.products = products
        self.added = []
        self.commits = 0
        self.flushes = 0

    def exec(self, statement):
        return FakeExecResult(self.cart)

    def get(self, model, key):
        return self.products.get(key)

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushes += 1

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        return None


def test_checkout_creates_order_items_and_decrements_stock(monkeypatch):
    cart = FakeCart(
        id=str(uuid4()),
        user_id=str(uuid4()),
        status=CartStatus.ACTIVE,
        items=[
            FakeCartItem(product_id="p1", quantity=2, unit_price=10.0),
            FakeCartItem(product_id="p2", quantity=1, unit_price=20.0),
        ],
    )
    products = {
        "p1": FakeProduct(id="p1", stock=5),
        "p2": FakeProduct(id="p2", stock=4),
    }
    session = FakeSession(cart=cart, products=products)

    monkeypatch.setattr(cart_crud, "select", lambda *args, **kwargs: FakeSelect())
    monkeypatch.setattr(cart_crud, "Order", FakeOrder)
    monkeypatch.setattr(cart_crud, "OrderItem", FakeOrderItem)

    result = cart_crud.checkout_cart(session, cart.user_id)

    assert result is not None
    checked_out_cart, order = result
    assert checked_out_cart.status == CartStatus.ORDERED
    assert order.total_amount == 40.0

    created_order_items = [
        obj for obj in session.added if isinstance(obj, FakeOrderItem)
    ]
    assert len(created_order_items) == 2

    assert products["p1"].stock == 3
    assert products["p2"].stock == 3
    assert session.flushes == 1
    assert session.commits == 1


def test_checkout_rejects_insufficient_stock_without_partial_commit(monkeypatch):
    cart = FakeCart(
        id=str(uuid4()),
        user_id=str(uuid4()),
        status=CartStatus.ACTIVE,
        items=[FakeCartItem(product_id="p1", quantity=2, unit_price=15.0)],
    )
    products = {"p1": FakeProduct(id="p1", stock=1)}
    session = FakeSession(cart=cart, products=products)

    monkeypatch.setattr(cart_crud, "select", lambda *args, **kwargs: FakeSelect())
    monkeypatch.setattr(cart_crud, "Order", FakeOrder)
    monkeypatch.setattr(cart_crud, "OrderItem", FakeOrderItem)

    with pytest.raises(ValueError, match="Insufficient stock"):
        cart_crud.checkout_cart(session, cart.user_id)

    assert products["p1"].stock == 1
    assert cart.status == CartStatus.ACTIVE
    assert session.flushes == 0
    assert session.commits == 0
