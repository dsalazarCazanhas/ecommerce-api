"""Smoke tests for public, users, products, cart, and admin routers.

These tests intentionally avoid ORM model instantiation and run against
in-memory doubles to validate core HTTP behavior quickly.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.v1.cart as cart_module
import src.api.v1.public as public_module
import src.api.v1.stripe as stripe_module
from src.api.v1.admin import router as admin_router
from src.api.v1.cart import router as cart_router
from src.api.v1.products import router as products_router
from src.api.v1.public import router as public_router
from src.api.v1.users import router as users_router
from src.config.engine import get_session
from src.crud import cart_crud, idempotency_crud, products_crud, users_crud
from src.models.auth import IdempotencyStatus
from src.security.auth import get_current_active_admin, get_current_user


@dataclass
class FakeUser:
    id: str
    name: str
    last_name: str
    username: str
    email: str
    phone: str
    role: str = "user"
    status: str = "active"
    failed_login_attempts: int = 0
    password_hash: str = "fake-hash"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None
    last_login: datetime | None = None


@dataclass
class FakeProduct:
    id: str
    name: str
    description: str | None
    price: float
    stock: int
    image_url: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None


@dataclass
class FakeCartItem:
    id: str
    cart_id: str
    product_id: str
    product: FakeProduct | None = None
    quantity: int = 1
    unit_price: float = 0.0


@dataclass
class FakeCart:
    id: str
    user_id: str
    status: str = "active"
    items: list[FakeCartItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None


@dataclass
class FakeOrder:
    id: str
    user_id: str
    status: str = "pending"
    total_amount: float = 0.0
    currency: str = "usd"
    stripe_session_id: str | None = None
    stripe_payment_intent_id: str | None = None
    updated_at: datetime | None = None


class PublicUserModel:
    """Lightweight stand-in used by public/register to avoid ORM initialization."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", str(uuid4()))
        self.name = kwargs["name"]
        self.last_name = kwargs["last_name"]
        self.username = kwargs["username"]
        self.email = kwargs["email"]
        self.phone = kwargs["phone"]
        self.role = kwargs.get("role", "user")
        self.status = kwargs.get("status", "active")
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.updated_at = kwargs.get("updated_at")
        self.last_login = kwargs.get("last_login")
        self.password_hash = kwargs.get("password_hash", "")


@dataclass
class UserStore:
    user: FakeUser
    users: dict[str, FakeUser] = field(default_factory=dict)

    def __post_init__(self):
        self.users[self.user.username] = self.user


@dataclass
class ProductStore:
    products: dict[str, FakeProduct] = field(default_factory=dict)


@dataclass
class CartStore:
    carts: dict[str, FakeCart] = field(default_factory=dict)


@pytest.fixture(name="fake_user")
def fake_user_fixture() -> FakeUser:
    return FakeUser(
        id=str(uuid4()),
        name="Smoke",
        last_name="User",
        username="smoke_user",
        email="smoke@example.com",
        phone="+12345678901",
    )


@pytest.fixture(name="fake_admin")
def fake_admin_fixture() -> FakeUser:
    return FakeUser(
        id=str(uuid4()),
        name="Smoke",
        last_name="Admin",
        username="smoke_admin",
        email="admin@example.com",
        phone="+12345678902",
        role="admin",
    )


@pytest.fixture(name="client")
def client_fixture(
    fake_user: FakeUser, fake_admin: FakeUser, monkeypatch: pytest.MonkeyPatch
):
    app = FastAPI(title="Smoke Test App", description="Smoke", version="0.1")
    app.include_router(public_router, prefix="/api/v1", tags=["Public"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
    app.include_router(products_router, prefix="/api/v1/products", tags=["Products"])
    app.include_router(cart_router, prefix="/api/v1/cart", tags=["Cart"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])

    session = SimpleNamespace(rollback=lambda: None)
    user_store = UserStore(user=fake_user)
    product_store = ProductStore()
    cart_store = CartStore()
    idempotency_store: dict[tuple[str, str, str], SimpleNamespace] = {}
    session.get = lambda model, obj_id: product_store.products.get(str(obj_id))

    def override_get_session():
        yield session

    def fake_get_user_by_username(username: str, session):
        return user_store.users.get(username)

    def fake_get_user_by_email(email: str, session):
        for user in user_store.users.values():
            if user.email == email:
                return user
        return None

    def fake_create_user(user, session):
        user_store.users[user.username] = user
        user_store.user = user
        return user

    def fake_update_user(user, session):
        user.updated_at = datetime.now(timezone.utc)
        user_store.users[user.username] = user
        user_store.user = user
        return user

    def fake_delete_user(username: str, session):
        if username in user_store.users:
            del user_store.users[username]
            return True
        return False

    def fake_get_products(session):
        return [vars(product) for product in product_store.products.values()]

    def fake_get_product_by_id(session, product_id):
        return product_store.products.get(str(product_id))

    def fake_get_product_by_name(session, name: str):
        for product in product_store.products.values():
            if product.name == name:
                return product
        return None

    def fake_create_product(session, product_data):
        product = FakeProduct(id=str(uuid4()), **product_data.model_dump())
        product_store.products[product.id] = product
        return product

    def fake_update_product(session, product):
        product.updated_at = datetime.now(timezone.utc)
        product_store.products[str(product.id)] = product
        return product

    def fake_delete_product(session, product_id):
        key = str(product_id)
        if key not in product_store.products:
            return False
        del product_store.products[key]
        return True

    def fake_get_active_cart(session, user_id: str):
        if user_id not in cart_store.carts:
            cart = FakeCart(id=str(uuid4()), user_id=user_id, status="active")
            cart_store.carts[user_id] = cart
            return cart
        return cart_store.carts[user_id]

    def fake_add_item_to_cart(
        session, cart: FakeCart, product: FakeProduct, quantity: int
    ):
        item_id = str(uuid4())
        item = FakeCartItem(
            id=item_id,
            cart_id=cart.id,
            product_id=product.id,
            product=product,
            quantity=quantity,
            unit_price=product.price,
        )
        cart.items.append(item)
        return item

    def fake_remove_item(session, item_id: str, user_id: str):
        cart = cart_store.carts.get(user_id)
        if not cart:
            return None
        for item in cart.items:
            if item.id == item_id:
                cart.items.remove(item)
                return True
        return None

    def fake_checkout_cart(session, user_id: str):
        cart = cart_store.carts.get(user_id)
        if not cart or not cart.items:
            return None
        cart.status = "ORDERED"
        cart.updated_at = datetime.now(timezone.utc)
        total_amount = sum(item.unit_price * item.quantity for item in cart.items)
        order = FakeOrder(id=str(uuid4()), user_id=user_id, total_amount=total_amount)
        return cart, order

    def fake_get_by_user_and_key(
        session,
        *,
        user_id: str,
        idempotency_key: str,
        scope: str,
    ):
        return idempotency_store.get((user_id, idempotency_key, scope))

    def fake_create_processing(
        session,
        *,
        user_id: str,
        idempotency_key: str,
        request_hash: str,
        scope: str,
    ):
        key = (user_id, idempotency_key, scope)
        existing = idempotency_store.get(key)
        if existing:
            return existing

        record = SimpleNamespace(
            user_id=user_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            status=IdempotencyStatus.PROCESSING,
            response_status_code=None,
            response_body=None,
        )
        idempotency_store[key] = record
        return record

    def fake_mark_completed(
        session,
        *,
        record,
        response_status_code: int,
        response_body: str,
    ):
        record.status = IdempotencyStatus.COMPLETED
        record.response_status_code = response_status_code
        record.response_body = response_body
        return record

    def fake_mark_failed(
        session,
        *,
        record,
        response_status_code: int,
        response_body: str,
    ):
        record.status = IdempotencyStatus.FAILED
        record.response_status_code = response_status_code
        record.response_body = response_body
        return record

    def fake_list_all_carts(session):
        return list(cart_store.carts.values())

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = lambda: user_store.user
    app.dependency_overrides[get_current_active_admin] = lambda: fake_admin

    monkeypatch.setattr(public_module, "User", PublicUserModel)

    monkeypatch.setattr(users_crud, "get_user_by_username", fake_get_user_by_username)
    monkeypatch.setattr(users_crud, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(users_crud, "create_user", fake_create_user)
    monkeypatch.setattr(users_crud, "update_user", fake_update_user)
    monkeypatch.setattr(users_crud, "delete_user_by_username", fake_delete_user)

    monkeypatch.setattr(products_crud, "get_products", fake_get_products)
    monkeypatch.setattr(products_crud, "get_product_by_id", fake_get_product_by_id)
    monkeypatch.setattr(products_crud, "get_product_by_name", fake_get_product_by_name)
    monkeypatch.setattr(products_crud, "create_product", fake_create_product)
    monkeypatch.setattr(products_crud, "update_product", fake_update_product)
    monkeypatch.setattr(products_crud, "delete_product", fake_delete_product)

    monkeypatch.setattr(cart_crud, "get_active_cart", fake_get_active_cart)
    monkeypatch.setattr(cart_crud, "add_item_to_cart", fake_add_item_to_cart)
    monkeypatch.setattr(cart_crud, "remove_item", fake_remove_item)
    monkeypatch.setattr(cart_crud, "checkout_cart", fake_checkout_cart)
    monkeypatch.setattr(cart_crud, "list_all_carts", fake_list_all_carts)

    monkeypatch.setattr(
        idempotency_crud,
        "get_by_user_and_key",
        fake_get_by_user_and_key,
    )
    monkeypatch.setattr(
        idempotency_crud,
        "create_processing",
        fake_create_processing,
    )
    monkeypatch.setattr(
        idempotency_crud,
        "mark_completed",
        fake_mark_completed,
    )
    monkeypatch.setattr(
        idempotency_crud,
        "mark_failed",
        fake_mark_failed,
    )

    client = TestClient(app, base_url="http://localhost", raise_server_exceptions=True)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Stripe smoke-test helpers and fixture
# ---------------------------------------------------------------------------


def _stripe_checkout_payload(order_id: str) -> dict:
    """Build a minimal valid CheckoutRequest payload for a given order id."""
    return {
        "order_id": order_id,
        "line_items": [
            {"name": "Widget", "currency": "usd", "amount": 1000, "quantity": 1}
        ],
        "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": "https://example.com/cancel",
    }


def _make_order(user_id: str) -> SimpleNamespace:
    """Create a mutable pending-order stub compatible with the Stripe handler."""
    return SimpleNamespace(
        id=str(uuid4()),
        user_id=user_id,
        status="pending",
        stripe_session_id=None,
        stripe_payment_intent_id=None,
        updated_at=None,
    )


@pytest.fixture(name="stripe_client")
def stripe_client_fixture(fake_user: FakeUser, monkeypatch: pytest.MonkeyPatch):
    """Minimal FastAPI app with only the Stripe router mounted.

    Yields a SimpleNamespace(client, order_store, user) so tests can seed
    orders and access the authenticated user's id without importing ORM models.
    """
    from src.api.v1.stripe import router as s_router
    from src.models.order import Order as OrderModel
    from src.services.stripe_service import StripeService

    app = FastAPI(title="Stripe Smoke", description="Stripe", version="0.1")
    app.include_router(s_router, prefix="/api/v1/stripe", tags=["Stripe"])

    order_store: dict[str, SimpleNamespace] = {}
    idempotency_store: dict[tuple[str, str, str], SimpleNamespace] = {}

    # Session stub — mutations on order objects propagate because we return the
    # same SimpleNamespace reference from order_store each time.
    session = SimpleNamespace(
        rollback=lambda: None,
        add=lambda obj: None,
        commit=lambda: None,
        refresh=lambda obj: None,
    )
    session.get = lambda model, obj_id: (
        order_store.get(str(obj_id)) if model is OrderModel else None
    )

    def override_get_session():
        yield session

    def fake_build_checkout_line_items(db, order):
        return [
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Server Widget"},
                    "unit_amount": 1000,
                },
                "quantity": 1,
            }
        ]

    # Idempotency CRUD fakes (scope-aware, mirrors the cart fixture)
    def fake_get_by_user_and_key(db, *, user_id, idempotency_key, scope):
        return idempotency_store.get((user_id, idempotency_key, scope))

    def fake_create_processing(db, *, user_id, idempotency_key, request_hash, scope):
        key = (user_id, idempotency_key, scope)
        existing = idempotency_store.get(key)
        if existing:
            return existing
        record = SimpleNamespace(
            user_id=user_id,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            status=IdempotencyStatus.PROCESSING,
            response_status_code=None,
            response_body=None,
        )
        idempotency_store[key] = record
        return record

    def fake_mark_completed(db, *, record, response_status_code, response_body):
        record.status = IdempotencyStatus.COMPLETED
        record.response_status_code = response_status_code
        record.response_body = response_body
        return record

    def fake_mark_failed(db, *, record, response_status_code, response_body):
        record.status = IdempotencyStatus.FAILED
        record.response_status_code = response_status_code
        record.response_body = response_body
        return record

    # Stripe SDK stub — avoids any real network calls
    def fake_stripe_create_checkout_session(
        line_items,
        success_url,
        cancel_url,
        mode="payment",
        payment_method_types=None,
        metadata=None,
        client_reference_id=None,
        idempotency_key=None,
    ):
        return {
            "id": "cs_test_fake123",
            "url": "https://checkout.stripe.com/pay/cs_test_fake123",
            "payment_intent": "pi_test_fake456",
        }

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = lambda: fake_user
    monkeypatch.setattr(
        idempotency_crud, "get_by_user_and_key", fake_get_by_user_and_key
    )
    monkeypatch.setattr(idempotency_crud, "create_processing", fake_create_processing)
    monkeypatch.setattr(idempotency_crud, "mark_completed", fake_mark_completed)
    monkeypatch.setattr(idempotency_crud, "mark_failed", fake_mark_failed)
    monkeypatch.setattr(
        stripe_module,
        "_build_checkout_line_items",
        fake_build_checkout_line_items,
    )
    # Replace the @staticmethod with a plain function; class-level access in
    # Python 3 does not bind args implicitly, so the call signature is preserved.
    monkeypatch.setattr(
        StripeService, "create_checkout_session", fake_stripe_create_checkout_session
    )

    tc = TestClient(app, base_url="http://localhost", raise_server_exceptions=True)
    ctx = SimpleNamespace(client=tc, order_store=order_store, user=fake_user)
    try:
        yield ctx
    finally:
        app.dependency_overrides.clear()


def test_public_root_and_health(client: TestClient):
    root_resp = client.get("/api/v1/")
    health_resp = client.get("/api/v1/health")

    assert root_resp.status_code == 200
    assert health_resp.status_code == 200
    assert health_resp.json() == {"status": "healthy"}
    assert "title" in root_resp.json()


def test_public_register_user(client: TestClient):
    resp = client.post(
        "/api/v1/register",
        json={
            "name": "New",
            "last_name": "User",
            "username": "new_user",
            "email": "new_user@example.com",
            "phone": "+12345678903",
            "password": "New@12345!",
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "new_user"
    assert body["email"] == "new_user@example.com"


def test_users_me_and_update(client: TestClient):
    me_resp = client.get("/api/v1/users/me")
    patch_resp = client.patch(
        "/api/v1/users/me",
        json={"name": "Renamed"},
    )

    assert me_resp.status_code == 200
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Renamed"


def test_products_register_list_and_delete(client: TestClient):
    create_resp = client.post(
        "/api/v1/products/register",
        json={
            "name": "Smoke Product",
            "description": "Smoke description",
            "price": 49.99,
            "stock": 10,
            "image_url": None,
        },
    )
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]

    list_resp = client.get("/api/v1/products/")
    delete_resp = client.delete(f"/api/v1/products/{product_id}")

    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert delete_resp.status_code == 204


def test_products_list_empty_collection(client: TestClient):
    list_resp = client.get("/api/v1/products/")

    assert list_resp.status_code == 200
    assert list_resp.json() == []


def test_products_update_missing_returns_404(client: TestClient):
    update_resp = client.patch(
        "/api/v1/products/4e8a51c0-7f55-4f70-8d13-278d3d6a1b7d",
        json={"name": "Updated Product"},
    )

    assert update_resp.status_code == 404
    assert update_resp.json()["detail"] == "Product not found."


def test_products_update_rejects_duplicate_name(client: TestClient):
    first_create = client.post(
        "/api/v1/products/register",
        json={
            "name": "First Product",
            "description": "First description",
            "price": 10.0,
            "stock": 5,
            "image_url": None,
        },
    )
    second_create = client.post(
        "/api/v1/products/register",
        json={
            "name": "Second Product",
            "description": "Second description",
            "price": 20.0,
            "stock": 7,
            "image_url": None,
        },
    )

    assert first_create.status_code == 201
    assert second_create.status_code == 201

    second_product_id = second_create.json()["id"]
    update_resp = client.patch(
        f"/api/v1/products/{second_product_id}",
        json={"name": "First Product"},
    )

    assert update_resp.status_code == 400
    assert update_resp.json()["detail"] == "Product already registered"


def test_admin_list_all_carts(client: TestClient):
    # List all carts (as admin)
    all_carts_resp = client.get("/api/v1/cart/admin/all")
    assert all_carts_resp.status_code == 200
    carts = all_carts_resp.json()
    assert isinstance(carts, list)


def test_checkout_requires_idempotency_key(client: TestClient):
    checkout_resp = client.post("/api/v1/cart/checkout")

    assert checkout_resp.status_code == 422


def test_checkout_replay_returns_same_summary(client: TestClient):
    create_resp = client.post(
        "/api/v1/products/register",
        json={
            "name": "Checkout Product",
            "description": "Checkout description",
            "price": 10.0,
            "stock": 5,
            "image_url": None,
        },
    )
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]

    add_resp = client.post(
        "/api/v1/cart/add",
        params={"product_id": product_id, "quantity": 2},
    )
    assert add_resp.status_code == 200

    key = str(uuid4())
    first_checkout = client.post(
        "/api/v1/cart/checkout",
        headers={"Idempotency-Key": key},
    )
    second_checkout = client.post(
        "/api/v1/cart/checkout",
        headers={"Idempotency-Key": key},
    )

    assert first_checkout.status_code == 200
    assert second_checkout.status_code == 200
    assert first_checkout.json() == second_checkout.json()


def test_checkout_same_key_different_hash_returns_conflict(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    key = str(uuid4())

    first_checkout = client.post(
        "/api/v1/cart/checkout",
        headers={"Idempotency-Key": key},
    )
    assert first_checkout.status_code == 400

    monkeypatch.setattr(
        cart_module,
        "_checkout_request_hash",
        lambda: "different-request-hash",
    )

    second_checkout = client.post(
        "/api/v1/cart/checkout",
        headers={"Idempotency-Key": key},
    )

    assert second_checkout.status_code == 409
    assert second_checkout.json()["detail"] == (
        "Idempotency-Key was already used with a different request"
    )


def test_admin_update_user(client: TestClient):
    # Update user as admin
    update_resp = client.patch(
        "/api/v1/admin/profile/smoke_user",
        json={"name": "Updated"},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "Updated"


# ---------------------------------------------------------------------------
# Stripe idempotency smoke tests
# ---------------------------------------------------------------------------


def test_stripe_checkout_requires_idempotency_key(
    stripe_client: SimpleNamespace,
):
    """POST /stripe/checkout without the Idempotency-Key header must return 422."""
    order = _make_order(stripe_client.user.id)
    stripe_client.order_store[order.id] = order

    resp = stripe_client.client.post(
        "/api/v1/stripe/checkout",
        json=_stripe_checkout_payload(order.id),
    )

    assert resp.status_code == 422


def test_stripe_checkout_replay_returns_same_response(
    stripe_client: SimpleNamespace,
):
    """Repeating the same Idempotency-Key + payload returns the cached response."""
    order = _make_order(stripe_client.user.id)
    stripe_client.order_store[order.id] = order
    key = str(uuid4())
    payload = _stripe_checkout_payload(order.id)

    first = stripe_client.client.post(
        "/api/v1/stripe/checkout",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    second = stripe_client.client.post(
        "/api/v1/stripe/checkout",
        json=payload,
        headers={"Idempotency-Key": key},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["session_id"] == "cs_test_fake123"


def test_stripe_checkout_rejects_foreign_order(
    stripe_client: SimpleNamespace,
):
    """Authenticated users must not create Stripe sessions for someone else's order."""
    foreign_order = _make_order(str(uuid4()))
    stripe_client.order_store[foreign_order.id] = foreign_order

    resp = stripe_client.client.post(
        "/api/v1/stripe/checkout",
        json=_stripe_checkout_payload(foreign_order.id),
        headers={"Idempotency-Key": str(uuid4())},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Order not found"


def test_stripe_checkout_same_key_different_payload_returns_conflict(
    stripe_client: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
):
    """Re-using an Idempotency-Key with a different payload hash must return 409."""
    order = _make_order(stripe_client.user.id)
    stripe_client.order_store[order.id] = order
    key = str(uuid4())
    payload = _stripe_checkout_payload(order.id)

    # First call: succeeds and persists the idempotency record with hash H1
    first = stripe_client.client.post(
        "/api/v1/stripe/checkout",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    assert first.status_code == 200

    # Simulate a tampered payload arriving with the same Idempotency-Key
    monkeypatch.setattr(
        stripe_module,
        "_stripe_checkout_request_hash",
        lambda data: "tampered-hash-differs-from-h1",
    )

    second = stripe_client.client.post(
        "/api/v1/stripe/checkout",
        json=payload,
        headers={"Idempotency-Key": key},
    )

    assert second.status_code == 409
    assert second.json()["detail"] == (
        "Idempotency-Key was already used with a different request"
    )
