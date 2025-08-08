# src/routers/auth.py
from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlmodel import Session, select

from src.config.engine import get_session
from src.security.creds import verify_password, create_access_token
from src.config.ext import settings
from src.security.auth import get_current_user
from src.models.users import User, UserResponse, UserRead, UserLogin
from src.utils.funcdb import get_user_by_username

router = APIRouter()

@router.post("/login", response_model=UserResponse, summary="User Login")
async def login(
    form_data: UserLogin,
    response: Response,
    session: Session = Depends(get_session)
):
    """
    Autenticar usuario y generar token JWT.
    
    - **username**: Username del usuario a loguear por username
    - **password**: Contraseña del usuario
    
    Retorna token JWT para usar en endpoints protegidos.
    """
    
    # Buscar usuario por username
    user = get_user_by_username(form_data.username, session)
    
    # Validar usuario y contraseña
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar que el usuario esté activo
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    session.expunge(user)
    session.add(user)
    session.commit()
    
    # Crear token JWT
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},  # 'sub' es el estándar para identificar usuario
        expires_delta=access_token_expires
    )

    # ✅ Cookie persistente con expiración
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE
    )
    
    # Retornar respuesta estructurada
    return UserResponse(
        user=UserRead.model_validate(user),
    )

@router.post("/refresh", summary="Refresh Token")
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    Renovar token JWT para usuario autenticado.
    Útil para mantener sesión activa sin re-login.
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/logout", summary="User Logout")
async def logout(response: Response):
    """Logout usuario eliminando la cookie"""
    response.delete_cookie(
        key="access_token",
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE
    )
    return {"message": "Logout successful"}