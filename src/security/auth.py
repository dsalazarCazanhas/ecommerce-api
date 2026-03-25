# src/security/auth.py
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from src.config.engine import SessionDep
from src.crud import users_crud
from src.models.users import User, UserStatus
from src.security.creds import security

# === DATA CLASSES ===


@dataclass
class RefreshClaims:
    """
    Validated refresh-token claims passed into the /refresh endpoint.

    Contains only JWT-extracted data (no DB query). Server-side validation
    (jti existence in DB and reuse detection) runs in the endpoint body so
    it can share the same DB session with rotation writes and avoid split
    transactions.
    """

    username: str  # sub claim - user identifier
    jti: UUID  # jti claim - current token to revoke during rotation
    family_id: UUID  # fid claim - family inherited by the next token


# === PRIVATE DEPENDENCIES ===


def _get_authenticated_user_from_cookie(
    request: Request,
    session: SessionDep,
    cookie_name: str,
    expected_token_type: str,
) -> User:
    token = request.cookies.get(cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You're not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = security.verify_token(token=token)

    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type: str = payload.get("token_type", "access")
    if token_type != expected_token_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = users_crud.get_user_by_username(username=username, session=session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account inactive"
        )

    return user


def get_current_user(
    request: Request,
    session: SessionDep,
) -> User:
    """
    Get current active user from token in cookies
    """
    return _get_authenticated_user_from_cookie(
        request=request,
        session=session,
        cookie_name="access_token",
        expected_token_type="access",
    )


def get_current_active_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Check if current user is admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required.",
        )
    return current_user


# === PUBLIC DEPENDENCIES (Phase 2) ===


def get_refresh_token_claims(request: Request) -> RefreshClaims:
    """
    FastAPI dependency for the /refresh endpoint.

    Performs cryptographic refresh-token validation (signature, expiration,
    token_type) and extracts claims needed for rotation.

    It does not query DB. DB checks are performed in the endpoint body so
    rotation reads and writes happen in a single DB session.

    Raises HTTP 401 when:
        - refresh_token cookie is missing
        - JWT is expired or signature is invalid
        - token_type is not "refresh"
        - jti or fid claims are missing or malformed
    """
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You're not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # verify_token raises HTTP 401 when the token is expired or invalid.
    payload = security.verify_token(token=token)

    # Reject access tokens presented via the refresh cookie.
    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: Optional[str] = payload.get("sub")
    raw_jti: Optional[str] = payload.get("jti")
    raw_fid: Optional[str] = payload.get("fid")

    if not username or not raw_jti or not raw_fid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Convert string claims to UUIDs for type safety downstream.
        jti = UUID(raw_jti)
        family_id = UUID(raw_fid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token claims",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return RefreshClaims(username=username, jti=jti, family_id=family_id)
