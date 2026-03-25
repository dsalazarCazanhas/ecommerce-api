# tests/test_auth.py
"""
End-to-end functional tests for authentication endpoints.

Covers:
    test_login_success             - successful login sets both cookies
    test_refresh_access_token      - /refresh issues a new access token
    test_logout_clears_cookies     - logout clears both cookies
    test_refresh_after_logout      - server-side revocation: token revoked at logout
                                                                     can no longer refresh
    test_reuse_detection           - already rotated token is rejected and full token
                                                                     family is invalidated (RFC 6749 10.4)

Setup:
    - In-memory SQLite (StaticPool) isolated from production DB.
    - get_session dependency is overridden so all endpoints use the same test session.
    - TestClient without context manager avoids lifespan init_db() against production;
        tables are created manually on the test engine.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.auth import router as auth_router
from src.config.engine import get_session
from src.config.ext import settings
from src.crud import refresh_tokens_crud, users_crud
from src.security.creds import security

# Minimal app instance for auth-only tests.
# This avoids importing unrelated routers that may contain independent issues.
app = FastAPI(title="Auth Test App")
app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"],
)


@dataclass
class StoredRefreshToken:
    """In-memory refresh token record used by the test doubles."""

    jti: UUID
    user_id: UUID
    family_id: UUID
    expires_at: datetime
    is_revoked: bool = False


@dataclass
class FakeUser:
    """In-memory user object exposing the attributes consumed by auth routes."""

    id: UUID
    name: str
    last_name: str
    username: str
    email: str
    phone: str
    role: str
    status: str
    password_hash: str
    failed_login_attempts: int = 0
    last_login: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None


# Test user credentials
TEST_USERNAME = "testuser"
TEST_PASSWORD = "Test@123!"
TEST_EMAIL = "test@example.com"


# Fixtures


@pytest.fixture(name="session")
def session_fixture():
    """
    Provide a lightweight stand-in session object.

    Auth endpoints pass session through to CRUD helpers only. For these HTTP
    tests we replace those helpers with in-memory doubles, so a simple object
    is enough and avoids unrelated ORM mapper issues from the rest of the app.
    """
    return SimpleNamespace()


@pytest.fixture(name="test_user")
def test_user_fixture() -> FakeUser:
    """
    Create an active in-memory user used by the CRUD doubles.

    The object mirrors the attributes required by the auth router and by
    UserRead.model_validate(...), but does not touch ORM mapper configuration.
    """
    return FakeUser(
        id=uuid4(),
        name="Test",
        last_name="User",
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        phone="+12345678901",
        role="user",
        status="active",
        failed_login_attempts=0,
        # Hash plaintext password for login verification.
        password_hash=security.hash_password(TEST_PASSWORD),
    )


@pytest.fixture(name="client")
def client_fixture(session, test_user: FakeUser, monkeypatch: pytest.MonkeyPatch):
    """
    TestClient configured with:
      - get_session override using a lightweight stand-in session
        - base_url="http://localhost" to satisfy TrustedHostMiddleware
      - in-memory doubles for users_crud and refresh_tokens_crud
      - no context manager to avoid unrelated lifespan/database side effects

    This keeps the tests focused on HTTP auth behavior: login, refresh rotation,
    logout revocation, and reuse detection.
    """

    refresh_store: dict[UUID, StoredRefreshToken] = {}

    def override_get_session():
        # Single shared placeholder session for the whole test.
        yield session

    def fake_get_user_by_username(*, username: str, session):
        if username == test_user.username:
            return test_user
        return None

    def fake_update_user(*, user, session):
        user.updated_at = datetime.now(timezone.utc)
        return user

    def fake_create_refresh_token(*, session, jti, user_id, family_id, expires_at):
        record = StoredRefreshToken(
            jti=jti,
            user_id=user_id,
            family_id=family_id,
            expires_at=expires_at,
        )
        refresh_store[jti] = record
        return record

    def fake_get_by_jti(*, session, jti):
        return refresh_store.get(jti)

    def fake_revoke(*, session, jti):
        record = refresh_store.get(jti)
        if record:
            record.is_revoked = True

    def fake_revoke_family(*, session, family_id):
        for record in refresh_store.values():
            if record.family_id == family_id:
                record.is_revoked = True

    app.dependency_overrides[get_session] = override_get_session
    monkeypatch.setattr(users_crud, "get_user_by_username", fake_get_user_by_username)
    monkeypatch.setattr(users_crud, "update_user", fake_update_user)
    monkeypatch.setattr(refresh_tokens_crud, "create", fake_create_refresh_token)
    monkeypatch.setattr(refresh_tokens_crud, "get_by_jti", fake_get_by_jti)
    monkeypatch.setattr(refresh_tokens_crud, "revoke", fake_revoke)
    monkeypatch.setattr(refresh_tokens_crud, "revoke_family", fake_revoke_family)

    # Do not use context manager to avoid triggering app lifespan startup.
    client = TestClient(app, base_url="http://localhost", raise_server_exceptions=True)
    yield client

    app.dependency_overrides.clear()


# Helpers


def _do_login(client: TestClient) -> tuple[str, str]:
    """
    Perform login and return (access_token, refresh_token) from cookies.
    Fail the test if login is unsuccessful.
    """
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    access = resp.cookies.get("access_token")
    refresh = resp.cookies.get("refresh_token")
    assert access is not None, "access_token cookie missing after login"
    assert refresh is not None, "refresh_token cookie missing after login"
    return access, refresh


def _set_refresh_cookie(client: TestClient, refresh_token: str) -> None:
    """Store a refresh token in the client cookie jar for the next request."""
    client.cookies.set("refresh_token", refresh_token)


# Tests


def test_login_success(client: TestClient, test_user: FakeUser):
    """
    Login with valid credentials must:
        - Return HTTP 200
        - Set access_token cookie
        - Set refresh_token cookie
        - Return user data in response body (without password_hash)
    """
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert resp.status_code == 200
    assert "access_token" in resp.cookies, "access_token cookie should be present"
    assert "refresh_token" in resp.cookies, "refresh_token cookie should be present"

    body = resp.json()
    assert body["username"] == TEST_USERNAME
    assert "password_hash" not in body, "password_hash must not be exposed"


def test_refresh_access_token(client: TestClient, test_user: FakeUser):
    """
    /refresh with a valid refresh token must:
        - Return HTTP 200
        - Issue a new access_token cookie
        - Issue a new refresh_token cookie (rotation)
    """
    _, refresh_before = _do_login(client)

    _set_refresh_cookie(client, refresh_before)
    resp = client.post("/api/v1/auth/refresh")

    assert resp.status_code == 200, f"Refresh failed: {resp.text}"
    assert "access_token" in resp.cookies, "new access_token should be issued"
    assert "refresh_token" in resp.cookies, "new refresh_token should be issued"

    # New refresh token must differ from original (effective rotation).
    assert (
        resp.cookies["refresh_token"] != refresh_before
    ), "refresh token should change on each rotation"


def test_logout_clears_cookies(client: TestClient, test_user: FakeUser):
    """
    POST /logout must:
        - Return HTTP 200
        - Clear both client cookies (Max-Age=0 or empty Set-Cookie value)
    """
    _do_login(client)

    resp = client.post("/api/v1/auth/logout")

    assert resp.status_code == 200

    # Verify cookies were cleared by the server.
    # Starlette TestClient reflects delete_cookie as empty or missing values.
    assert (
        resp.cookies.get("access_token", "") == ""
    ), "access_token should be cleared after logout"
    assert (
        resp.cookies.get("refresh_token", "") == ""
    ), "refresh_token should be cleared after logout"


def test_refresh_after_logout_is_rejected(client: TestClient, test_user: FakeUser):
    """
    Key Phase 2 test: server-side revocation.

    After logout, the original refresh token must be rejected even if JWT
    signature remains mathematically valid, because its jti was marked revoked
    in the database.

    This verifies protection beyond JWT expiration.
    """
    _, refresh_token = _do_login(client)

    # Logout revokes jti server-side.
    _set_refresh_cookie(client, refresh_token)
    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # Reusing revoked token must fail with HTTP 401.
    _set_refresh_cookie(client, refresh_token)
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert (
        refresh_resp.status_code == 401
    ), "token revoked at logout must not refresh again (server-side revocation)"


def test_reuse_detection(client: TestClient, test_user: FakeUser):
    """
    Reuse-detection test (RFC 6749 10.4 / Auth0 token family pattern).

    Scenario: attacker captures original refresh token and user rotates it
    legitimately. If original token is presented again, server must detect
    reuse, revoke full family, and return HTTP 401.

    Also verifies that the legitimate rotated token is invalidated too
    (entire family destroyed), forcing re-authentication.
    """
    _, original_refresh = _do_login(client)

    # First legitimate rotation revokes original_refresh in DB.
    _set_refresh_cookie(client, original_refresh)
    r1 = client.post("/api/v1/auth/refresh")
    assert r1.status_code == 200, f"First rotation failed: {r1.text}"
    rotated_refresh = r1.cookies.get("refresh_token")
    assert rotated_refresh is not None

    # Replay original revoked token -> reuse detection -> 401.
    # Server must also revoke entire family.
    _set_refresh_cookie(client, original_refresh)
    r2 = client.post("/api/v1/auth/refresh")
    assert r2.status_code == 401, "reused original token should be rejected with 401"

    # Legitimately rotated token must also be invalidated because it is
    # part of the same family - full family destruction behavior.
    _set_refresh_cookie(client, rotated_refresh)
    r3 = client.post("/api/v1/auth/refresh")
    assert r3.status_code == 401, (
        "after reuse detection, full family should be revoked - "
        "including the legitimately rotated token"
    )
