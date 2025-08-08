# src/utils/funcdb.py
from typing import Optional
from sqlmodel import Session, select
from src.config.engine import get_session
from src.models.users import User

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