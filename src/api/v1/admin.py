from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from datetime import datetime, timezone

from src.security.creds import security
from src.config.engine import get_session
from src.crud import users_crud
from src.models.users import User, UserAdmin, UserCreate, UserRead, UserUpdate
from src.security.auth import get_current_user, get_current_active_admin


router = APIRouter()

# === Authenticated as Admin ===

@router.get("/profile/{username}", response_model=UserAdmin, summary="Get user profile as admin")
async def get_user_profile_as_admin(username: str, session: Session = Depends(get_session)):
    """Get user info only visible for admins"""
    user = users_crud.get_user_by_username(username, session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserAdmin.model_validate(user)

@router.delete("/delete/{username}", summary="Delete user")
async def delete_user(
    username: str,
    session: Session = Depends(get_session),
):
    """Eliminar usuario con validaciones administrativas"""
    current_admin: User = get_current_active_admin(session=session)
    if current_admin.username == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself."
        )
    try:
        users_crud.get_user_by_username(username, session)
    except HTTPException:
        raise HTTPException(status_code=404, detail="User not found.")
    return users_crud.delete_user(username, session)

@router.patch("/profile/{username}", response_model=UserUpdate, summary="Update user as admin")
async def update_user_as_admin(
    user_update: UserUpdate,
    username: str,
    session: Session = Depends(get_session)):
    """Actualizar usuario siendo admin"""
    user = users_crud.get_user_by_username(username, session)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    """Actualizar datos del usuario"""
    if user_update.email and user_update.email != user.email:
        existing_email = users_crud.get_user_by_email(user_update.email, session)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )

    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    return users_crud.update_user(user, session)