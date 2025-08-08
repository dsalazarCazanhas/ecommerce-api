# src/security/auth.py
from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from jose import JWTError, jwt

from src.config.engine import get_session
from src.config.ext import settings
from src.models.users import User

# Esquema OAuth2 - FastAPI automáticamente agregará el botón "Authorize" en docs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def verify_token(token: str) -> Optional[dict]:
    """
    Verificar y decodificar JWT token
    Retorna el payload si es válido, None si no
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        return payload
    except JWTError:
        return None

def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
) -> User:
    """
    Dependencia para obtener el usuario actual desde el JWT token en la cookie
    Se usa en endpoints que requieren autenticación
    """
    
    # Obtener el token desde la cookie 'access_token'
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar y decodificar token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validar campos del payload
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

    # Buscar usuario en base de datos
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar estado del usuario
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
    Dependencia para endpoints que requieren rol de admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user