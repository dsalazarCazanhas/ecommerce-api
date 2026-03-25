# src/routers/auth.py
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from src.config.engine import SessionDep
from src.config.ext import settings
from src.crud import refresh_tokens_crud, users_crud
from src.models.users import UserLogin, UserRead, UserStatus
from src.security.auth import RefreshClaims, get_refresh_token_claims
from src.security.creds import security

router = APIRouter()

# Used to keep login timing similar for existing and non-existing users.
DUMMY_PASSWORD_HASH = security.hash_password("dummy-password-not-used")


def _set_auth_no_store_headers(response: Response) -> None:
    """Prevent caches from storing authentication responses."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _refresh_cookie_path() -> str:
    return f"{settings.API_V1_STR}/auth/refresh"


def _set_access_cookie(response: Response, access_token: str) -> None:
    """
    Set the access_token cookie with configured security attributes.

    This cookie keeps a broad path ('/') because access_token is required on
    most authenticated API requests. Its short lifetime
    (ACCESS_TOKEN_EXPIRE_MINUTES) limits exposure if compromised.
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """
    Set refresh_token cookie restricted to the /refresh endpoint path.

    Path restriction is defense-in-depth: the browser sends this cookie only
    on POST /api/v1/auth/refresh, reducing exposure on unrelated API calls.
    The longer lifetime (REFRESH_TOKEN_EXPIRE_DAYS) is balanced by Phase 2
    server-side revocation.
    """
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=_refresh_cookie_path(),
    )


def _clear_auth_cookies(response: Response) -> None:
    """
    Remove both authentication cookies from the client.

    Note: this is client-side cleanup only. Real refresh-token revocation
    (server-side) must happen before calling this helper, inside logout.
    """
    response.delete_cookie(
        key="access_token",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=_refresh_cookie_path(),
    )


@router.post(
    "/login",
    response_model=UserRead,
    summary="User Login",
    status_code=status.HTTP_200_OK,
)
async def login(
    form_data: UserLogin,
    response: Response,
    session: SessionDep,
):
    """
    Authenticate user and return JWT token.

    - **username**: User username
    - **password**: User password

    Returns a JWT token in an HTTP-only cookie upon successful authentication.
    """

    # Search for user by username
    user = users_crud.get_user_by_username(username=form_data.username, session=session)

    # Verify username and password
    if not user:
        security.verify_password(
            plain_password=form_data.password, hashed_password=DUMMY_PASSWORD_HASH
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not security.verify_password(
        plain_password=form_data.password, hashed_password=user.password_hash
    ):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.status = UserStatus.INACTIVE
            users_crud.update_user(user=user, session=session)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive due to too many failed login attempts",
            )

        users_crud.update_user(user=user, session=session)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    user.failed_login_attempts = 0
    user.last_login = datetime.now(timezone.utc)
    users_crud.update_user(user=user, session=session)

    # Issue short-lived access token without DB persistence (crypto-only validation).
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Issue long-lived refresh token and start a new rotation family.
    # Metadata (jti, family_id, expires_at) is persisted in DB to enable
    # Phase 2 server-side revocation and reuse detection.
    refresh_data = security.create_refresh_token(data={"sub": user.username})
    refresh_tokens_crud.create(
        session=session,
        jti=refresh_data.jti,
        user_id=user.id,
        family_id=refresh_data.family_id,
        expires_at=refresh_data.expires_at,
    )

    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, refresh_data.token)
    _set_auth_no_store_headers(response)

    return UserRead.model_validate(user)


@router.post("/refresh", summary="Refresh Token", status_code=status.HTTP_200_OK)
async def refresh_token(
    response: Response,
    session: SessionDep,
    claims: RefreshClaims = Depends(get_refresh_token_claims),
):
    """
    Rotate refresh token and issue a new access token.

    Security flow (Phase 2):
       1. get_refresh_token_claims already validated signature, expiration, and type.
       2. Verify jti exists in DB (rejects pre-Phase-2 and forged tokens).
       3. Reuse detection: if jti is already revoked, revoke the whole family
           and return 401.
       4. Revoke current token and issue a new one in the same family.
       5. Persist the new token in DB.
    """
    # Verify jti existence in DB.
    # Missing jti may indicate a pre-Phase-2 token or a forged token.
    record = refresh_tokens_crud.get_by_jti(session=session, jti=claims.jti)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not recognized — please log in again",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reuse detection: a revoked jti presented again indicates possible token replay.
    # Revoke the full family so neither attacker nor user can continue this chain.
    if record.is_revoked:
        refresh_tokens_crud.revoke_family(session=session, family_id=claims.family_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected — session invalidated for security",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ensure user still exists and is active.
    user = users_crud.get_user_by_username(username=claims.username, session=session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive",
        )

    # Revoke current token before issuing next one (same-session atomic rotation).
    refresh_tokens_crud.revoke(session=session, jti=claims.jti)

    # Issue new access token.
    access_token = security.create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    # Issue new refresh token in the same family to continue the session chain.
    new_refresh = security.create_refresh_token(
        data={"sub": user.username},
        family_id=claims.family_id,  # keep family_id to continue this family
    )

    # Persist new refresh token in DB.
    refresh_tokens_crud.create(
        session=session,
        jti=new_refresh.jti,
        user_id=user.id,
        family_id=claims.family_id,
        expires_at=new_refresh.expires_at,
    )

    _set_access_cookie(response, access_token)
    _set_refresh_cookie(response, new_refresh.token)
    _set_auth_no_store_headers(response)

    return {"message": "Token refreshed"}


@router.post("/logout", summary="User Logout", status_code=status.HTTP_200_OK)
async def logout(request: Request, response: Response, session: SessionDep):
    """
    Close user session.

    Phase 2 server-side revocation: if refresh_token cookie exists and is valid,
    its jti is marked revoked in DB before client-side cookie deletion. This
    prevents replay even if the token was previously stolen.

    Idempotent: always clears client cookies even when token is expired,
    missing from DB, or already revoked.
    """
    token = request.cookies.get("refresh_token")
    if token:
        try:
            # Decode JWT to extract jti.
            # verify_token raises HTTPException on expired/invalid token;
            # both cases are intentionally ignored to keep logout idempotent.
            payload = security.verify_token(token)
            raw_jti = payload.get("jti")
            if raw_jti:
                # Best-effort DB revocation; no failure if already revoked.
                refresh_tokens_crud.revoke(session=session, jti=UUID(raw_jti))
        except (HTTPException, ValueError):
            # Expired/invalid token or malformed jti - nothing to revoke in DB;
            # continue to clear client cookies.
            pass

    _clear_auth_cookies(response)
    _set_auth_no_store_headers(response)
    return {"message": "Logout successful"}
