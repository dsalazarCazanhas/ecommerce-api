# src/security/auth.py
from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from src.config.engine import get_session
from src.crud import users_crud
from src.models.users import User, UserRead
from src.security.creds import security


def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
) -> UserRead:
    """
    Get current active user from token in cookies
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You're not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token
    payload = security.verify_token(token=token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token contents
    username: Optional[str] = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_expires_at = payload.get("exp")
    if not token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing expiration",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_expires_at < int(datetime.now().timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Search user in DB
    user = users_crud.get_user_by_username(username=username, session=session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive"
        )

    return user

def get_current_active_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Check if current user is admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user
