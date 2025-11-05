# src/routers/auth.py
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from src.config.engine import get_session
from src.crud import users_crud
from src.security.creds import security
from src.config.ext import settings
from src.security.auth import get_current_user
from src.models.users import User, UserRead, UserLogin


router = APIRouter()

@router.post("/login", response_model=UserRead, summary="User Login")
async def login(
    form_data: UserLogin,
    response: Response,
    session: Session = Depends(get_session)
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
    if not user or not security.verify_password(plain_password=form_data.password, hashed_password=user.password_hash):
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.status = "inactive"
            users_crud.update_user(user=user, session=session)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive due to too many failed login attempts"
            )
        user.failed_login_attempts += 1
        users_crud.update_user(user=user, session=session)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    user.last_login = datetime.now(timezone.utc)
    users_crud.update_user(user=user, session=session)
    
    # Create JWT token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    # Persistent cookie with token
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE
    )
    
    return UserRead.model_validate(user)

@router.post("/refresh", summary="Refresh Token")
async def refresh_token(
    response: Response,
    current_user: User = Depends(get_current_user)
):
    """Refresh JWT token for the current user."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": current_user.username},
        expires_delta=access_token_expires
    )

    # Update cookie with new token
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE
    )

    return {"message": "Token refreshed"}

@router.post("/logout", summary="User Logout")
async def logout(response: Response, _: User = Depends(get_current_user)):
    """Logout usuario eliminando la cookie"""
    response.delete_cookie(
        key="access_token",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE
    )
    return {"message": "Logout successful"}