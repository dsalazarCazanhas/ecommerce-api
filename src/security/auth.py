# src/security/auth.py
from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from src.config.engine import get_session
from src.models.users import User
from src.security.creds import security



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
            detail="You're not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar y decodificar token
    payload = security.verify_token(token)
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


def get_user_by_username(username: str, session: Session) -> Optional[User]:
    """
    Obtener usuario por username desde la base de datos.
    
    Args:
        username (str): El username del usuario a buscar
        session (Session, optional): Sesión de DB. Si no se proporciona, crea una nueva.
    
    Returns:
        User: El objeto User si se encuentra, None si no existe
    """
    
    try:
        # Ejecutar la consulta
        result = session.exec(select(User).where(User.username == username))
        return result.first()
    except Exception as e:
        # Log del error si tienes logging configurado
        print(f"Error querying user by username {username}: {e}")
        return None

def get_user_by_email(email: str, session: Session = None) -> Optional[User]:
    """
    Obtener usuario por email desde la base de datos.
    Función auxiliar útil para login y validaciones
    """
    if session is None:
        session = next(get_session())
    
    try:
        result = session.exec(select(User).where(User.email == email))
        return result.first()
    except Exception as e:
        print(f"Error querying user by email {email}: {e}")
        return None