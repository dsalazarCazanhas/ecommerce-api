from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timezone

from src.config.engine import get_session
from src.security.auth import get_current_user
from src.utils.funcdb import get_user_by_username
from src.security.creds import hash_password
from src.models.users import User, UserCreate, UserRead, UserUpdate, UserPublic

router = APIRouter()

# === ENDPOINTS PÚBLICOS ===

@router.post("/register", response_model=UserRead, summary="Register New User")
async def register_user(
    user_data: UserCreate,
    session: Session = Depends(get_session)
) -> UserRead:
    """Registrar un nuevo usuario"""

    # NO uses 'with session' - la dependencia ya maneja esto
    # Verificar si username ya existe
    existing_username = get_user_by_username(user_data.username)
    
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Verificar si email ya existe
    existing_email = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash del password
    hashed_password = hash_password(user_data.password)

    # Crear usuario - CLAVE: convertir a dict primero
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict["password_hash"] = hashed_password
    
    # Crear instancia del modelo User
    db_user = User(**user_dict)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return UserRead.model_validate(db_user)

# === ENDPOINTS AUTENTICADOS ===
# NOTA: Estos endpoints necesitan una función de autenticación real

@router.get("/me", summary="Get Current User")
async def get_current_user_info(
    # TODO: Cambiar por una función de autenticación real
    current_user: User = Depends(get_current_user)
):
    """Obtener información del usuario actual"""
    return UserRead.model_validate(current_user)

@router.patch("/me", summary="Update Current User", response_model=None)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_user_by_username),
    session: Session = Depends(get_session)
):
    """Actualizar información del usuario actual"""
    
    # Si se intenta cambiar email, verificar que no exista
    if user_update.email and user_update.email != current_user.email:
        existing_email = session.exec(
            select(User).where(
                (User.email == user_update.email) & 
                (User.id != current_user.id)
            )
        ).first()
        
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
    
    # Actualizar campos
    user_data = user_update.model_dump(exclude_unset=True)
    for field, value in user_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.now(timezone.utc)
    
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    
    return current_user  # ✅ Add this line
    

@router.get("/profile/{username}", response_model=UserPublic, summary="Get User Profile")
async def get_user_profile(
    username: str,
    session: Session = Depends(get_session)
) -> UserPublic:
    """Obtener perfil público de un usuario"""
    
    user = get_user_by_username(username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserPublic.model_validate(user)